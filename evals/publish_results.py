from __future__ import annotations

import argparse
import hashlib
import json
import math
import shutil
import statistics
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from evals.scoring import score_workspace
from evals.validation import load_jsonl, validate_dataset

PROJECT_ROOT = Path(__file__).resolve().parents[1]
COMPATIBILITY_KEYS = (
    "protocol_version",
    "dataset_version",
    "dataset_sha256",
    "provider",
    "model_name",
    "model_base_url",
    "model_max_input_tokens",
    "reasoning_effort",
    "temperature",
    "timeout_seconds",
    "max_provider_retries",
    "concurrency",
    "deepagents_recursion_limit",
    "search_call_limit",
    "search_timeout_seconds",
    "search_max_retries",
    "fetch_call_limit",
    "fetch_timeout_seconds",
    "fetch_max_retries",
    "fetch_max_bytes",
    "fetch_max_chars",
    "researcher_call_limit",
    "analyst_call_limit",
    "editor_call_limit",
    "draft_edit_call_limit",
    "run_date",
)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


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


def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.write_text(
        "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows),
        encoding="utf-8",
    )


def _nearest_rank(values: list[int], percentile: float) -> int | None:
    if not values:
        return None
    ordered = sorted(values)
    rank = max(1, math.ceil(percentile * len(ordered)))
    return ordered[rank - 1]


def _discover_latest_runs(
    results_root: Path,
    case_ids: set[str],
) -> dict[str, tuple[Path, dict[str, Any], dict[str, Any]]]:
    candidates: dict[str, list[tuple[Path, dict[str, Any], dict[str, Any]]]] = {
        case_id: [] for case_id in case_ids
    }
    for result_dir in sorted(results_root.iterdir()):
        if not result_dir.is_dir() or result_dir.name == "published":
            continue
        config_path = result_dir / "config.json"
        raw_path = result_dir / "raw_runs.jsonl"
        if not config_path.is_file() or not raw_path.is_file():
            continue
        config = json.loads(config_path.read_text(encoding="utf-8"))
        for raw in _read_jsonl(raw_path):
            case_id = str(raw.get("case_id") or "")
            if case_id in candidates:
                candidates[case_id].append((result_dir, config, raw))

    missing = sorted(case_id for case_id, rows in candidates.items() if not rows)
    if missing:
        raise ValueError(f"missing source runs for cases: {missing}")

    return {
        case_id: max(
            rows,
            key=lambda item: str(
                item[2].get("started_at") or item[2].get("finished_at") or ""
            ),
        )
        for case_id, rows in candidates.items()
    }


def _validate_compatible_runs(
    selected: dict[str, tuple[Path, dict[str, Any], dict[str, Any]]],
    dataset_path: Path,
) -> dict[str, Any]:
    ordered = [selected[case_id][1] for case_id in sorted(selected)]
    baseline = ordered[0]
    for key in COMPATIBILITY_KEYS:
        values = {json.dumps(config.get(key), sort_keys=True) for config in ordered}
        if len(values) != 1:
            raise ValueError(f"incompatible source configuration for {key}: {values}")
    dataset_digest = _sha256(dataset_path)
    if baseline.get("dataset_sha256") != dataset_digest:
        raise ValueError("source run dataset hash does not match the selected dataset")
    return baseline


def _artifact_manifest(workspace: Path, score: dict[str, Any]) -> list[dict[str, Any]]:
    manifest: list[dict[str, Any]] = []
    relative_paths = {
        relative
        for paths in (score.get("artifact_files") or {}).values()
        for relative in paths
    }
    for relative in sorted(relative_paths):
        artifact = workspace / relative
        if artifact.is_file():
            manifest.append(
                {
                    "path": relative,
                    "sha256": _sha256(artifact),
                    "size_bytes": artifact.stat().st_size,
                }
            )
    return manifest


def _compact_run(
    case: dict[str, Any],
    result_dir: Path,
    raw: dict[str, Any],
    output_dir: Path,
) -> tuple[dict[str, Any], dict[str, Any]]:
    metadata = raw.get("metadata") or {}
    workspace = result_dir / "workspaces" / case["id"] / "workspace"
    if metadata and workspace.is_dir():
        score = score_workspace(
            workspace,
            case,
            metadata,
            final_text=raw.get("final_text"),
        )
        status = "completed" if score["completed"] else "agent_failure"
        failure_type = None if score["completed"] else "acceptance_criteria"
    else:
        score = raw.get("score") or {}
        status = str(raw.get("status") or "infrastructure_failure")
        failure_type = raw.get("failure_type")

    report_source: str | None = None
    report_paths = (score.get("artifact_files") or {}).get("report") or []
    if report_paths and workspace.is_dir():
        source = workspace / report_paths[-1]
        if source.is_file():
            reports_dir = output_dir / "reports"
            reports_dir.mkdir(parents=True, exist_ok=True)
            destination = reports_dir / f"{case['id']}.md"
            shutil.copy2(source, destination)
            report_source = destination.relative_to(output_dir).as_posix()

    usage = metadata.get("usage") or {}
    calls = {
        key: metadata.get(key)
        for key in (
            "llm_calls",
            "search_calls",
            "fetch_calls",
            "fetch_attempts",
            "fetch_duplicate_rejections",
            "researcher_calls",
            "researcher_attempts",
            "researcher_rejections",
            "analyst_calls",
            "editor_calls",
            "draft_edit_calls",
        )
    }
    compact = {
        "case_id": case["id"],
        "category": case.get("category"),
        "language": case.get("language"),
        "source_result_dir": result_dir.name,
        "started_at": raw.get("started_at"),
        "finished_at": raw.get("finished_at"),
        "original_status": raw.get("status"),
        "original_failure_type": raw.get("failure_type"),
        "status": status,
        "failure_type": failure_type,
        "rescored": True,
        "status_changed_by_rescore": status != raw.get("status"),
        "langfuse_trace_id": raw.get("langfuse_trace_id"),
        "latency_ms": raw.get("latency_ms"),
        "usage": {
            "llm_calls": usage.get("llm_calls"),
            "input_tokens": usage.get("input_tokens"),
            "output_tokens": usage.get("output_tokens"),
            "total_tokens": usage.get("total_tokens"),
        },
        "calls": calls,
        "score": score,
        "published_report": report_source,
    }
    manifest = {
        "case_id": case["id"],
        "source_result_dir": result_dir.name,
        "source_raw_runs_sha256": _sha256(result_dir / "raw_runs.jsonl"),
        "source_config_sha256": _sha256(result_dir / "config.json"),
        "artifacts": _artifact_manifest(workspace, score) if workspace.is_dir() else [],
    }
    return compact, manifest


def _all_checks_pass(run: dict[str, Any], field: str) -> bool:
    checks = (run.get("score") or {}).get(field) or {}
    return bool(checks) and all(checks.values())


def _build_summary(runs: list[dict[str, Any]]) -> dict[str, Any]:
    statuses = Counter(str(run["status"]) for run in runs)
    tokens = [
        int(run["usage"]["total_tokens"])
        for run in runs
        if run.get("usage", {}).get("total_tokens") is not None
    ]
    latencies = [
        int(run["latency_ms"])
        for run in runs
        if run.get("latency_ms") is not None
    ]
    count = len(runs)
    completed = statuses["completed"]
    return {
        "run_count": count,
        "completed_count": completed,
        "completion_rate": completed / count if count else 0,
        "status_counts": {
            status: statuses[status]
            for status in ("completed", "agent_failure", "infrastructure_failure")
        },
        "artifact_completeness_rate": (
            sum(float(run["score"].get("artifact_completeness") or 0) for run in runs)
            / count
            if count
            else 0
        ),
        "language_compliance_rate": (
            sum(bool(run["score"].get("language_compliance")) for run in runs) / count
            if count
            else 0
        ),
        "budget_compliance_rate": (
            sum(_all_checks_pass(run, "budget_checks") for run in runs) / count
            if count
            else 0
        ),
        "source_link_compliance_rate": (
            sum(_all_checks_pass(run, "source_link_checks") for run in runs) / count
            if count
            else 0
        ),
        "tokens": {
            "sample_count": len(tokens),
            "total": sum(tokens),
            "mean": round(statistics.fmean(tokens), 2) if tokens else None,
            "median": statistics.median(tokens) if tokens else None,
            "p95_nearest_rank": _nearest_rank(tokens, 0.95),
        },
        "latency_ms": {
            "sample_count": len(latencies),
            "total": sum(latencies),
            "mean": round(statistics.fmean(latencies), 2) if latencies else None,
            "median": statistics.median(latencies) if latencies else None,
            "p95_nearest_rank": _nearest_rank(latencies, 0.95),
        },
        "status_changes_from_rescore": sum(
            bool(run["status_changed_by_rescore"]) for run in runs
        ),
        "cost": {
            "status": "pending_langfuse_export",
            "total_usd": None,
            "projected_50_run_cost_with_20_percent_buffer_usd": None,
        },
        "percentile_method": "nearest-rank for P95; standard median for P50",
    }


def _write_report(
    output_dir: Path,
    config: dict[str, Any],
    runs: list[dict[str, Any]],
    summary: dict[str, Any],
) -> None:
    rows = [
        "| {case} | {status} | {latency} | {tokens} | {citations} | {changed} |".format(
            case=run["case_id"],
            status=run["status"],
            latency=run["latency_ms"],
            tokens=run["usage"]["total_tokens"],
            citations=run["score"].get("citation_count", "n/a"),
            changed="yes" if run["status_changed_by_rescore"] else "no",
        )
        for run in runs
    ]
    report = "\n".join(
        [
            "# Published Deep Research Smoke Evaluation",
            "",
            f"- Protocol: `{config['protocol_version']}`",
            f"- Model: `{config['model_name']}`",
            f"- Dataset SHA-256: `{config['dataset_sha256']}`",
            f"- Scorer SHA-256: `{config['scorer_sha256']}`",
            f"- Completion: {summary['completed_count']}/{summary['run_count']}",
            "- Cost status: pending Langfuse export",
            "",
            "| Case | Status | Latency (ms) | Total tokens | Citations | Status changed by rescore |",
            "| --- | --- | ---: | ---: | ---: | --- |",
            *rows,
            "",
            "## Aggregate Metrics",
            "",
            f"- Completion rate: {summary['completion_rate']:.2%}",
            f"- Artifact completeness rate: {summary['artifact_completeness_rate']:.2%}",
            f"- Language compliance rate: {summary['language_compliance_rate']:.2%}",
            f"- Budget compliance rate: {summary['budget_compliance_rate']:.2%}",
            f"- Source-link compliance rate: {summary['source_link_compliance_rate']:.2%}",
            f"- Median total tokens: {summary['tokens']['median']}",
            f"- P95 total tokens: {summary['tokens']['p95_nearest_rank']}",
            f"- Median latency: {summary['latency_ms']['median']} ms",
            f"- P95 latency: {summary['latency_ms']['p95_nearest_rank']} ms",
            "",
            "## Audit Notes",
            "",
            "- Source `raw_runs.jsonl` files were not modified.",
            "- Every selected workspace was rescored with the scorer hash above.",
            "- The latest run per fixed case ID was selected before rescoring.",
            "- Final reports are copied under `reports/`; supporting artifact hashes are in `manifest.json`.",
            "- Smoke metrics validate the harness and are excluded from the main benchmark.",
            "",
        ]
    )
    (output_dir / "report.md").write_text(report, encoding="utf-8")


def publish_results(
    dataset_path: Path,
    results_root: Path,
    output_dir: Path,
) -> dict[str, Any]:
    validation = validate_dataset(dataset_path)
    if validation["errors"]:
        raise ValueError("dataset validation failed: " + "; ".join(validation["errors"]))
    cases = load_jsonl(dataset_path)
    case_by_id = {str(case["id"]): case for case in cases}
    selected = _discover_latest_runs(results_root, set(case_by_id))
    baseline = _validate_compatible_runs(selected, dataset_path)
    if output_dir.exists():
        raise FileExistsError(f"published output already exists: {output_dir}")
    output_dir.mkdir(parents=True)

    scorer_path = PROJECT_ROOT / "evals/scoring.py"
    published_at = datetime.now(UTC).isoformat()
    config = {
        key: baseline.get(key)
        for key in COMPATIBILITY_KEYS
    }
    config.update(
        {
            "publication_schema_version": 1,
            "published_at": published_at,
            "selection_policy": "latest run per fixed dataset case ID",
            "selected_case_ids": sorted(case_by_id),
            "source_result_dirs": sorted(
                {result_dir.name for result_dir, _config, _raw in selected.values()}
            ),
            "source_git_commits": sorted(
                {str(config.get("git_commit") or "unknown") for _dir, config, _raw in selected.values()}
            ),
            "scorer_sha256": _sha256(scorer_path),
        }
    )

    runs: list[dict[str, Any]] = []
    manifests: list[dict[str, Any]] = []
    for case_id in sorted(case_by_id):
        result_dir, _source_config, raw = selected[case_id]
        compact, manifest = _compact_run(
            case_by_id[case_id], result_dir, raw, output_dir
        )
        runs.append(compact)
        manifests.append(manifest)

    summary = _build_summary(runs)
    manifest = {
        "publication_schema_version": 1,
        "published_at": published_at,
        "dataset_sha256": config["dataset_sha256"],
        "scorer_sha256": config["scorer_sha256"],
        "cases": manifests,
    }
    _write_json(output_dir / "config.json", config)
    _write_jsonl(output_dir / "rescored_runs.jsonl", runs)
    _write_json(output_dir / "summary.json", summary)
    _write_json(output_dir / "manifest.json", manifest)
    _write_report(output_dir, config, runs, summary)
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Publish an immutable, compact, offline-rescored evaluation bundle"
    )
    parser.add_argument(
        "--dataset",
        default="evals/datasets/research_smoke_v1.jsonl",
    )
    parser.add_argument(
        "--results-root",
        default="evals/results",
    )
    parser.add_argument(
        "--output-dir",
        default="evals/results/published/smoke_v1",
    )
    args = parser.parse_args()
    summary = publish_results(
        (PROJECT_ROOT / args.dataset).resolve(),
        (PROJECT_ROOT / args.results_root).resolve(),
        (PROJECT_ROOT / args.output_dir).resolve(),
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
