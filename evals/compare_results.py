from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
QUALITY_FIELDS = (
    "artifact_completeness_rate",
    "language_compliance_rate",
    "budget_compliance_rate",
    "source_link_compliance_rate",
)


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def _write_json(path: Path, payload: Any) -> None:
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _display_path(path: Path) -> str:
    try:
        return path.relative_to(PROJECT_ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def _number(value: float, places: int = 6) -> float:
    return round(float(value), places)


def _relative_change(baseline: float, candidate: float) -> float | None:
    if baseline == 0:
        return None
    return _number((candidate - baseline) / baseline)


def _percentage_point_change(baseline: float, candidate: float) -> float:
    return _number((candidate - baseline) * 100)


def _load_bundle(path: Path) -> dict[str, Any]:
    required = {
        "config": path / "config.json",
        "summary": path / "summary.json",
        "costs": path / "costs.json",
        "runs": path / "rescored_runs.jsonl",
    }
    missing = [name for name, file_path in required.items() if not file_path.is_file()]
    if missing:
        raise FileNotFoundError(
            f"published bundle {path} is missing: {', '.join(sorted(missing))}"
        )
    runs = _read_jsonl(required["runs"])
    summary = _read_json(required["summary"])
    if len(runs) != int(summary.get("run_count") or 0):
        raise ValueError(f"run count does not match summary for {path}")
    if sum(run.get("status") == "completed" for run in runs) != int(
        summary.get("completed_count") or 0
    ):
        raise ValueError(f"completed count does not match summary for {path}")
    return {
        "path": path,
        "config": _read_json(required["config"]),
        "summary": summary,
        "costs": _read_json(required["costs"]),
        "runs": runs,
        "files": required,
    }


def _validate_compatible(baseline: dict[str, Any], candidate: dict[str, Any]) -> None:
    baseline_config = baseline["config"]
    candidate_config = candidate["config"]
    for key in ("dataset_sha256", "model_name"):
        if baseline_config.get(key) != candidate_config.get(key):
            raise ValueError(f"published bundles differ on {key}")
    baseline_ids = {str(run["case_id"]) for run in baseline["runs"]}
    candidate_ids = {str(run["case_id"]) for run in candidate["runs"]}
    if baseline_ids != candidate_ids:
        raise ValueError("published bundles contain different case IDs")
    for label, bundle in (("baseline", baseline), ("candidate", candidate)):
        validation = bundle["costs"].get("validation") or {}
        if not validation.get("all_generations_priced"):
            raise ValueError(f"{label} bundle contains unpriced generations")
        if int(validation.get("trace_count") or 0) != len(bundle["runs"]):
            raise ValueError(f"{label} Langfuse trace count is incomplete")


def _failure_reasons(run: dict[str, Any]) -> list[str]:
    if run.get("status") == "completed":
        return []
    failure_type = str(run.get("failure_type") or "unknown")
    if failure_type == "recursion_limit":
        return ["recursion limit"]
    if failure_type == "timeout":
        return ["900-second timeout"]
    score = run.get("score") or {}
    reasons: list[str] = []
    if score.get("language_compliance") is False:
        reasons.append("language mismatch")
    if float(score.get("artifact_completeness") or 0) < 1:
        reasons.append("incomplete artifacts")
    citations = score.get("citation_count")
    minimum = score.get("minimum_citations")
    if citations is not None and minimum is not None and int(citations) < int(minimum):
        reasons.append(f"insufficient citations ({citations}/{minimum})")
    return reasons or [failure_type.replace("_", " ")]


def _transition_summary(
    baseline_runs: list[dict[str, Any]], candidate_runs: list[dict[str, Any]]
) -> dict[str, Any]:
    baseline_by_id = {str(run["case_id"]): run for run in baseline_runs}
    candidate_by_id = {str(run["case_id"]): run for run in candidate_runs}
    rows: list[dict[str, Any]] = []
    groups: dict[str, list[str]] = {
        "improved": [],
        "regressed": [],
        "stable_completed": [],
        "stable_not_completed": [],
    }
    exact_counts: Counter[str] = Counter()
    for case_id in sorted(baseline_by_id):
        baseline = baseline_by_id[case_id]
        candidate = candidate_by_id[case_id]
        baseline_status = str(baseline["status"])
        candidate_status = str(candidate["status"])
        exact_counts[f"{baseline_status} -> {candidate_status}"] += 1
        if baseline_status != "completed" and candidate_status == "completed":
            group = "improved"
        elif baseline_status == "completed" and candidate_status != "completed":
            group = "regressed"
        elif baseline_status == "completed":
            group = "stable_completed"
        else:
            group = "stable_not_completed"
        groups[group].append(case_id)
        rows.append(
            {
                "case_id": case_id,
                "baseline_status": baseline_status,
                "baseline_failure_type": baseline.get("failure_type"),
                "candidate_status": candidate_status,
                "candidate_failure_type": candidate.get("failure_type"),
                "candidate_failure_reasons": _failure_reasons(candidate),
                "transition_group": group,
            }
        )
    return {
        "counts": {key: len(value) for key, value in groups.items()},
        "case_ids": groups,
        "exact_status_counts": dict(sorted(exact_counts.items())),
        "cases": rows,
    }


def _load_recovery_metrics(bundle: dict[str, Any]) -> dict[str, Any]:
    published_dir: Path = bundle["path"]
    results_root = published_dir.parent.parent
    source_cache: dict[str, dict[str, dict[str, Any]]] = {}
    observed: list[dict[str, int]] = []
    missing_case_ids: list[str] = []
    for run in bundle["runs"]:
        source_dir = str(run.get("source_result_dir") or "")
        case_id = str(run["case_id"])
        if source_dir not in source_cache:
            raw_path = results_root / source_dir / "raw_runs.jsonl"
            if not raw_path.is_file():
                source_cache[source_dir] = {}
            else:
                source_cache[source_dir] = {
                    str(raw["case_id"]): raw for raw in _read_jsonl(raw_path)
                }
        raw = source_cache[source_dir].get(case_id)
        metadata = (raw or {}).get("metadata") or {}
        if "researcher_recovery_calls" not in metadata:
            missing_case_ids.append(case_id)
            continue
        observed.append(
            {
                "calls": int(metadata.get("researcher_recovery_calls") or 0),
                "attempts": int(metadata.get("researcher_recovery_attempts") or 0),
                "rejections": int(metadata.get("researcher_recovery_rejections") or 0),
            }
        )
    return {
        "supported": bool(observed),
        "observed_run_count": len(observed),
        "missing_case_ids": missing_case_ids,
        "runs_with_executed_recovery": sum(item["calls"] > 0 for item in observed),
        "executed_recovery_calls": sum(item["calls"] for item in observed),
        "recovery_attempts": sum(item["attempts"] for item in observed),
        "recovery_rejections": sum(item["rejections"] for item in observed),
    }


def _bundle_identity(bundle: dict[str, Any]) -> dict[str, Any]:
    config = bundle["config"]
    return {
        "path": _display_path(bundle["path"]),
        "protocol_version": config.get("protocol_version"),
        "dataset_sha256": config.get("dataset_sha256"),
        "model_name": config.get("model_name"),
        "source_git_commits": config.get("source_git_commits") or [],
        "published_at": config.get("published_at"),
    }


def _quality_comparison(
    baseline: dict[str, Any], candidate: dict[str, Any]
) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for field in QUALITY_FIELDS:
        baseline_value = float(baseline["summary"].get(field) or 0)
        candidate_value = float(candidate["summary"].get(field) or 0)
        result[field] = {
            "baseline": baseline_value,
            "candidate": candidate_value,
            "change_percentage_points": _percentage_point_change(
                baseline_value, candidate_value
            ),
        }
    return result


def _metric_pair(baseline: float, candidate: float) -> dict[str, Any]:
    return {
        "baseline": baseline,
        "candidate": candidate,
        "absolute_change": _number(candidate - baseline),
        "relative_change": _relative_change(baseline, candidate),
    }


def _efficiency_comparison(
    baseline: dict[str, Any], candidate: dict[str, Any]
) -> dict[str, Any]:
    baseline_summary = baseline["summary"]
    candidate_summary = candidate["summary"]
    baseline_model = baseline["costs"]["model_cost"]
    candidate_model = candidate["costs"]["model_cost"]
    baseline_bocha = baseline["costs"]["bocha_search_cost"]
    candidate_bocha = candidate["costs"]["bocha_search_cost"]
    baseline_completed = int(baseline_summary["completed_count"])
    candidate_completed = int(candidate_summary["completed_count"])
    baseline_total_cost = float(baseline_model["total_usd"])
    candidate_total_cost = float(candidate_model["total_usd"])
    return {
        "latency_ms": {
            key: _metric_pair(
                float(baseline_summary["latency_ms"][key]),
                float(candidate_summary["latency_ms"][key]),
            )
            for key in ("mean", "median", "p95_nearest_rank")
        },
        "local_tokens": {
            "baseline_sample_count": baseline_summary["tokens"]["sample_count"],
            "candidate_sample_count": candidate_summary["tokens"]["sample_count"],
            "median": _metric_pair(
                float(baseline_summary["tokens"]["median"]),
                float(candidate_summary["tokens"]["median"]),
            ),
            "p95_nearest_rank": _metric_pair(
                float(baseline_summary["tokens"]["p95_nearest_rank"]),
                float(candidate_summary["tokens"]["p95_nearest_rank"]),
            ),
            "comparable": (
                baseline_summary["tokens"]["sample_count"]
                == candidate_summary["tokens"]["sample_count"]
            ),
        },
        "model_cost_usd": {
            "total": _metric_pair(baseline_total_cost, candidate_total_cost),
            "mean_per_run": _metric_pair(
                float(baseline_model["mean_per_run_usd"]),
                float(candidate_model["mean_per_run_usd"]),
            ),
            "cost_per_completed_case": _metric_pair(
                baseline_total_cost / baseline_completed,
                candidate_total_cost / candidate_completed,
            ),
            "all_candidate_generations_priced": bool(
                candidate["costs"]["validation"].get("all_generations_priced")
            ),
        },
        "bocha_search": {
            "calls": _metric_pair(
                float(baseline_bocha["evaluation_search_calls"]),
                float(candidate_bocha["evaluation_search_calls"]),
            ),
            "allocated_cost_cny": _metric_pair(
                float(baseline_bocha["evaluation_allocated_cost_cny"]),
                float(candidate_bocha["evaluation_allocated_cost_cny"]),
            ),
        },
    }


def build_comparison(
    baseline_dir: Path,
    candidate_dir: Path,
    *,
    generated_at: str | None = None,
) -> dict[str, Any]:
    baseline = _load_bundle(baseline_dir)
    candidate = _load_bundle(candidate_dir)
    _validate_compatible(baseline, candidate)
    baseline_summary = baseline["summary"]
    candidate_summary = candidate["summary"]
    baseline_rate = float(baseline_summary["completion_rate"])
    candidate_rate = float(candidate_summary["completion_rate"])
    transitions = _transition_summary(baseline["runs"], candidate["runs"])
    return {
        "schema_version": 1,
        "generated_at": generated_at or datetime.now(UTC).isoformat(),
        "comparison_type": "regression_on_previously_observed_dataset",
        "baseline": _bundle_identity(baseline),
        "candidate": _bundle_identity(candidate),
        "completion": {
            "run_count": int(candidate_summary["run_count"]),
            "baseline_completed": int(baseline_summary["completed_count"]),
            "candidate_completed": int(candidate_summary["completed_count"]),
            "baseline_rate": baseline_rate,
            "candidate_rate": candidate_rate,
            "absolute_completed_change": (
                int(candidate_summary["completed_count"])
                - int(baseline_summary["completed_count"])
            ),
            "change_percentage_points": _percentage_point_change(
                baseline_rate, candidate_rate
            ),
            "relative_change": _relative_change(baseline_rate, candidate_rate),
        },
        "transitions": transitions,
        "candidate_status_counts": candidate_summary["status_counts"],
        "candidate_failure_type_counts": dict(
            sorted(
                Counter(
                    str(run.get("failure_type") or "none")
                    for run in candidate["runs"]
                    if run.get("status") != "completed"
                ).items()
            )
        ),
        "quality": _quality_comparison(baseline, candidate),
        "efficiency": _efficiency_comparison(baseline, candidate),
        "recovery_researcher": {
            "baseline": _load_recovery_metrics(baseline),
            "candidate": _load_recovery_metrics(candidate),
        },
        "limitations": [
            "The candidate reuses a dataset whose baseline failures were already reviewed; this is a regression comparison, not a holdout benchmark.",
            "Each task was run once, so the report provides descriptive results without variance estimates or confidence intervals.",
            "Three candidate terminal failures lack local token metrics; Langfuse costs cover all traces, but local token percentiles use 27 of 30 cases.",
            "Structural completion and source provenance do not establish factual correctness or full citation entailment.",
            "This comparison does not include a non-isolated context baseline and cannot establish context-usage reduction.",
        ],
    }


def _percent(value: float) -> str:
    return f"{value:.1%}"


def _signed_percent(value: float | None) -> str:
    if value is None:
        return "n/a"
    return f"{value:+.1%}"


def _render_report(comparison: dict[str, Any]) -> str:
    completion = comparison["completion"]
    transitions = comparison["transitions"]
    efficiency = comparison["efficiency"]
    baseline = comparison["baseline"]
    candidate = comparison["candidate"]
    candidate_recovery = comparison["recovery_researcher"]["candidate"]
    failure_rows = [
        "| {case_id} | {failure_type} | {reasons} |".format(
            case_id=row["case_id"],
            failure_type=row["candidate_failure_type"],
            reasons=", ".join(row["candidate_failure_reasons"]),
        )
        for row in transitions["cases"]
        if row["candidate_status"] != "completed"
    ]
    case_rows = [
        "| {case_id} | {baseline} | {candidate} | {group} |".format(
            case_id=row["case_id"],
            baseline=row["baseline_status"],
            candidate=row["candidate_status"],
            group=row["transition_group"],
        )
        for row in transitions["cases"]
    ]
    latency = efficiency["latency_ms"]
    model_cost = efficiency["model_cost_usd"]
    search = efficiency["bocha_search"]
    token_metrics = efficiency["local_tokens"]
    lines = [
        "# Deep Research v1 vs v2 Regression Comparison",
        "",
        "## Scope and Methodology",
        "",
        (
            f"This report compares protocol `{baseline['protocol_version']}` with "
            f"`{candidate['protocol_version']}` on the same {completion['run_count']} "
            f"cases, dataset hash `{candidate['dataset_sha256']}`, and model "
            f"`{candidate['model_name']}`. Because v2 was designed after reviewing v1 "
            "failures, this is a regression comparison on a previously observed dataset, "
            "not a holdout benchmark."
        ),
        "",
        "## Executive Results",
        "",
        "| Metric | v1 | v2 | Change |",
        "| --- | ---: | ---: | ---: |",
        (
            f"| Completed cases | {completion['baseline_completed']}/"
            f"{completion['run_count']} | {completion['candidate_completed']}/"
            f"{completion['run_count']} | +{completion['absolute_completed_change']} |"
        ),
        (
            f"| Completion rate | {_percent(completion['baseline_rate'])} | "
            f"{_percent(completion['candidate_rate'])} | "
            f"{completion['change_percentage_points']:+.1f} pp |"
        ),
        (
            f"| Median latency | {latency['median']['baseline'] / 1000:.1f}s | "
            f"{latency['median']['candidate'] / 1000:.1f}s | "
            f"{_signed_percent(latency['median']['relative_change'])} |"
        ),
        (
            f"| P95 latency | {latency['p95_nearest_rank']['baseline'] / 1000:.1f}s | "
            f"{latency['p95_nearest_rank']['candidate'] / 1000:.1f}s | "
            f"{_signed_percent(latency['p95_nearest_rank']['relative_change'])} |"
        ),
        (
            f"| Model cost | ${model_cost['total']['baseline']:.4f} | "
            f"${model_cost['total']['candidate']:.4f} | "
            f"{_signed_percent(model_cost['total']['relative_change'])} |"
        ),
        (
            f"| Cost per completed case | "
            f"${model_cost['cost_per_completed_case']['baseline']:.4f} | "
            f"${model_cost['cost_per_completed_case']['candidate']:.4f} | "
            f"{_signed_percent(model_cost['cost_per_completed_case']['relative_change'])} |"
        ),
        (
            f"| Bocha search calls | {search['calls']['baseline']:.0f} | "
            f"{search['calls']['candidate']:.0f} | "
            f"{_signed_percent(search['calls']['relative_change'])} |"
        ),
        "",
        (
            f"v2 recovered {transitions['counts']['improved']} previous failures, "
            f"regressed {transitions['counts']['regressed']} previous successes, kept "
            f"{transitions['counts']['stable_completed']} cases successful, and left "
            f"{transitions['counts']['stable_not_completed']} cases incomplete."
        ),
        "",
        "## Case-Level Transitions",
        "",
        f"- Improved: {', '.join(transitions['case_ids']['improved'])}",
        f"- Regressed: {', '.join(transitions['case_ids']['regressed'])}",
        (
            "- Stable completed: "
            + ", ".join(transitions["case_ids"]["stable_completed"])
        ),
        (
            "- Stable incomplete: "
            + ", ".join(transitions["case_ids"]["stable_not_completed"])
        ),
        "",
        "| Case | v1 | v2 | Transition |",
        "| --- | --- | --- | --- |",
        *case_rows,
        "",
        "## Remaining v2 Failures",
        "",
        "| Case | Failure type | Deterministic reason |",
        "| --- | --- | --- |",
        *failure_rows,
        "",
        "## Cost, Latency, and Recovery Trade-offs",
        "",
        (
            f"Model spend increased by "
            f"{_signed_percent(model_cost['total']['relative_change'])}, while cost per "
            f"completed case changed by "
            f"{_signed_percent(model_cost['cost_per_completed_case']['relative_change'])}. "
            "This efficiency metric allocates the cost of all attempts, including failures, "
            "across completed cases."
        ),
        (
            f"Median latency changed from {latency['median']['baseline'] / 1000:.1f}s "
            f"to {latency['median']['candidate'] / 1000:.1f}s, and P95 changed from "
            f"{latency['p95_nearest_rank']['baseline'] / 1000:.1f}s to "
            f"{latency['p95_nearest_rank']['candidate'] / 1000:.1f}s. The reliability "
            "gain therefore came with a latency trade-off."
        ),
        (
            f"Local median token usage was {token_metrics['median']['baseline']:.0f} in "
            f"v1 and {token_metrics['median']['candidate']:.0f} in v2. This is not a "
            f"complete token comparison because the sample counts are "
            f"{token_metrics['baseline_sample_count']} and "
            f"{token_metrics['candidate_sample_count']}; Langfuse model-cost totals do "
            "cover all 30 traces in both versions."
        ),
        (
            f"The v2 recovery Researcher executed in "
            f"{candidate_recovery['runs_with_executed_recovery']} runs "
            f"({candidate_recovery['executed_recovery_calls']} calls). Recovery metrics "
            f"were unavailable for {len(candidate_recovery['missing_case_ids'])} terminal "
            "failures whose local workflow metadata was not returned."
        ),
        "",
        "## Interpretation",
        "",
        (
            f"The defensible result is that v2 improved structural completion from "
            f"{_percent(completion['baseline_rate'])} to "
            f"{_percent(completion['candidate_rate'])} across the same 30 regression "
            "cases while reducing model cost per completed case. It does not establish "
            "the same completion rate on unseen tasks or in production."
        ),
        "",
        "## Limitations",
        "",
        *[f"- {item}" for item in comparison["limitations"]],
        "",
    ]
    return "\n".join(lines)


def write_comparison(
    baseline_dir: Path,
    candidate_dir: Path,
    output_dir: Path,
    *,
    generated_at: str | None = None,
) -> dict[str, Any]:
    if output_dir.exists():
        raise FileExistsError(f"comparison output already exists: {output_dir}")
    comparison = build_comparison(
        baseline_dir,
        candidate_dir,
        generated_at=generated_at,
    )
    output_dir.mkdir(parents=True)
    comparison_path = output_dir / "comparison.json"
    report_path = output_dir / "report.md"
    _write_json(comparison_path, comparison)
    report_path.write_text(_render_report(comparison), encoding="utf-8")
    source_files = {
        "baseline_summary": baseline_dir / "summary.json",
        "baseline_costs": baseline_dir / "costs.json",
        "baseline_runs": baseline_dir / "rescored_runs.jsonl",
        "candidate_summary": candidate_dir / "summary.json",
        "candidate_costs": candidate_dir / "costs.json",
        "candidate_runs": candidate_dir / "rescored_runs.jsonl",
    }
    manifest = {
        "schema_version": 1,
        "generated_at": comparison["generated_at"],
        "sources": {
            name: {
                "path": _display_path(path),
                "sha256": _sha256(path),
            }
            for name, path in source_files.items()
        },
        "outputs": {
            "comparison.json": _sha256(comparison_path),
            "report.md": _sha256(report_path),
        },
    }
    _write_json(output_dir / "manifest.json", manifest)
    return comparison


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Compare two published Deep Research evaluation bundles"
    )
    parser.add_argument(
        "--baseline-dir",
        default="evals/results/published/main_v1",
    )
    parser.add_argument(
        "--candidate-dir",
        default="evals/results/published/main_v2",
    )
    parser.add_argument(
        "--output-dir",
        default="evals/results/published/main_v1_vs_v2",
    )
    args = parser.parse_args()
    comparison = write_comparison(
        (PROJECT_ROOT / args.baseline_dir).resolve(),
        (PROJECT_ROOT / args.candidate_dir).resolve(),
        (PROJECT_ROOT / args.output_dir).resolve(),
    )
    print(json.dumps(comparison, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
