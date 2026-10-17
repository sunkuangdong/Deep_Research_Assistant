from __future__ import annotations

import argparse
import hashlib
import json
import statistics
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


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


def _required_json(directory: Path, names: tuple[str, ...]) -> dict[str, Any]:
    loaded: dict[str, Any] = {}
    for name in names:
        path = directory / name
        if not path.is_file():
            raise FileNotFoundError(f"missing published artifact: {path}")
        loaded[name] = _read_json(path)
    return loaded


def _median_task_cv(per_task: list[dict[str, Any]], metric: str) -> float | None:
    values = [
        float(task[metric]["coefficient_of_variation"])
        for task in per_task
        if task.get(metric, {}).get("coefficient_of_variation") is not None
    ]
    return round(statistics.median(values), 6) if values else None


def _validate_sources(
    comparison: dict[str, Any],
    stability_config: dict[str, Any],
    stability_summary: dict[str, Any],
    stability_costs: dict[str, Any],
) -> None:
    candidate = comparison["candidate"]
    for key in ("dataset_sha256", "model_name", "protocol_version"):
        if candidate.get(key) != stability_config.get(key):
            raise ValueError(f"comparison and stability bundles differ on {key}")
    if comparison.get("comparison_type") != (
        "regression_on_previously_observed_dataset"
    ):
        raise ValueError("comparison evidence must be labeled as regression")
    if int(stability_summary.get("task_count") or 0) != 10:
        raise ValueError("stability evidence must contain ten tasks")
    if int(stability_summary.get("observation_count") or 0) != 30:
        raise ValueError("stability evidence must contain thirty observations")
    if int(stability_config.get("repeat_count") or 0) != 3:
        raise ValueError("stability evidence must contain three repeats")
    full_cost = (stability_costs.get("stability_cost") or {}).get("full_v2_experiment")
    if not full_cost:
        raise ValueError("stability evidence lacks deduplicated experiment cost")
    if int(full_cost.get("total_unique_paid_run_count") or 0) != 50:
        raise ValueError("full v2 experiment must contain fifty unique paid runs")
    if not full_cost.get("within_model_spend_cap"):
        raise ValueError("full v2 experiment exceeded the model spend cap")
    if not full_cost.get("within_search_call_cap"):
        raise ValueError("full v2 experiment exceeded the search-call cap")


def build_final_summary(
    comparison_dir: Path,
    stability_dir: Path,
    *,
    generated_at: str | None = None,
) -> dict[str, Any]:
    comparison_files = _required_json(
        comparison_dir,
        ("comparison.json", "manifest.json"),
    )
    stability_files = _required_json(
        stability_dir,
        ("config.json", "summary.json", "costs.json", "manifest.json"),
    )
    comparison = comparison_files["comparison.json"]
    stability_config = stability_files["config.json"]
    stability = stability_files["summary.json"]
    stability_costs = stability_files["costs.json"]
    _validate_sources(comparison, stability_config, stability, stability_costs)

    completion = comparison["completion"]
    efficiency = comparison["efficiency"]
    agreement = stability["completion_agreement"]
    per_task = stability["per_task"]
    stable_completed = [
        task["case_id"] for task in per_task if task["completed_runs"] == 3
    ]
    stable_incomplete = [
        task["case_id"] for task in per_task if task["completed_runs"] == 0
    ]
    mixed = [task["case_id"] for task in per_task if not task["completion_agreement"]]
    full_cost = stability_costs["stability_cost"]["full_v2_experiment"]
    additional_cost = stability_costs["stability_cost"]["additional_stability_runs"]
    return {
        "schema_version": 1,
        "generated_at": generated_at or datetime.now(UTC).isoformat(),
        "model_name": comparison["candidate"]["model_name"],
        "dataset_sha256": comparison["candidate"]["dataset_sha256"],
        "protocols": {
            "baseline": comparison["baseline"]["protocol_version"],
            "candidate": comparison["candidate"]["protocol_version"],
        },
        "main_regression": {
            "evidence_type": "regression_on_previously_observed_dataset",
            "task_count": completion["run_count"],
            "baseline_completed": completion["baseline_completed"],
            "candidate_completed": completion["candidate_completed"],
            "baseline_completion_rate": completion["baseline_rate"],
            "candidate_completion_rate": completion["candidate_rate"],
            "change_percentage_points": completion["change_percentage_points"],
            "improved_case_count": comparison["transitions"]["counts"]["improved"],
            "regressed_case_count": comparison["transitions"]["counts"]["regressed"],
            "candidate_status_counts": comparison["candidate_status_counts"],
            "candidate_failure_type_counts": comparison[
                "candidate_failure_type_counts"
            ],
        },
        "efficiency_tradeoffs": {
            "median_latency_ms": efficiency["latency_ms"]["median"],
            "p95_latency_ms": efficiency["latency_ms"]["p95_nearest_rank"],
            "model_cost_usd": efficiency["model_cost_usd"]["total"],
            "cost_per_completed_case_usd": efficiency["model_cost_usd"][
                "cost_per_completed_case"
            ],
            "search_calls": efficiency["bocha_search"]["calls"],
        },
        "stability": {
            "evidence_type": "post_regression_frozen_subset_not_holdout",
            "task_count": stability["task_count"],
            "runs_per_task": stability["repeat_count"],
            "observation_count": stability["observation_count"],
            "completed_observations": stability["completed_observation_count"],
            "pooled_completion_rate": stability["pooled_completion_rate"],
            "three_run_completion_agreement_rate": agreement["rate"],
            "three_run_exact_status_agreement_rate": stability[
                "exact_status_agreement"
            ]["rate"],
            "stable_completed_case_ids": stable_completed,
            "stable_incomplete_case_ids": stable_incomplete,
            "mixed_outcome_case_ids": mixed,
            "completion_frequency_distribution": agreement["frequency_distribution"],
            "median_within_task_token_cv": _median_task_cv(per_task, "tokens"),
            "median_within_task_latency_cv": _median_task_cv(per_task, "latency_ms"),
            "token_observation_sample_count": stability["tokens"]["sample_count"],
            "token_observation_missing_count": stability["tokens"]["missing_count"],
            "latency_observation_sample_count": stability["latency_ms"]["sample_count"],
            "latency_observation_missing_count": stability["latency_ms"][
                "missing_count"
            ],
        },
        "deduplicated_v2_experiment_cost": {
            "main_run_count": full_cost["main_run_count"],
            "additional_stability_run_count": full_cost[
                "additional_stability_run_count"
            ],
            "total_unique_paid_run_count": full_cost["total_unique_paid_run_count"],
            "additional_stability_model_cost_usd": additional_cost["model_cost_usd"],
            "total_model_cost_usd": full_cost["model_cost_usd"],
            "total_search_calls": full_cost["search_calls"],
            "within_model_spend_cap": full_cost["within_model_spend_cap"],
            "within_search_call_cap": full_cost["within_search_call_cap"],
        },
        "defensible_claims": [
            (
                "Protocol v2 improved structural completion from 36.7% to 80.0% "
                "across the same 30-case regression dataset."
            ),
            (
                "Model cost per completed case decreased by 41.8%, despite a "
                "26.9% increase in total model cost."
            ),
            (
                "A frozen ten-task subset achieved 76.7% pooled completion and "
                "70.0% three-run outcome agreement."
            ),
        ],
        "unsupported_claims": [
            "The 80.0% completion rate generalizes to unseen or production tasks.",
            "The system guarantees factual correctness or citation entailment.",
            "Context isolation reduced token usage without a non-isolated baseline.",
            "The ten-task stability subset is independent holdout evidence.",
        ],
    }


def _percent(value: float) -> str:
    return f"{value:.1%}"


def _render_report(summary: dict[str, Any]) -> str:
    main = summary["main_regression"]
    efficiency = summary["efficiency_tradeoffs"]
    stability = summary["stability"]
    cost = summary["deduplicated_v2_experiment_cost"]
    median_latency = efficiency["median_latency_ms"]
    p95_latency = efficiency["p95_latency_ms"]
    total_cost = efficiency["model_cost_usd"]
    cost_per_completed = efficiency["cost_per_completed_case_usd"]
    return "\n".join(
        [
            "# Final Deep Research Benchmark Report",
            "",
            "## Executive Summary",
            "",
            (
                f"Protocol v2 completed {main['candidate_completed']}/"
                f"{main['task_count']} regression tasks "
                f"({_percent(main['candidate_completion_rate'])}), up from "
                f"{main['baseline_completed']}/{main['task_count']} "
                f"({_percent(main['baseline_completion_rate'])}) in v1. This is a "
                f"{main['change_percentage_points']:.1f} percentage-point increase."
            ),
            (
                f"On the frozen ten-task stability subset, the system completed "
                f"{stability['completed_observations']}/"
                f"{stability['observation_count']} observations "
                f"({_percent(stability['pooled_completion_rate'])}) and produced "
                f"the same completion outcome in all three runs for "
                f"{len(stability['stable_completed_case_ids']) + len(stability['stable_incomplete_case_ids'])}/"
                f"{stability['task_count']} tasks "
                f"({_percent(stability['three_run_completion_agreement_rate'])})."
            ),
            "",
            "## Evaluation Design",
            "",
            f"- Model: `{summary['model_name']}`.",
            f"- Dataset SHA-256: `{summary['dataset_sha256']}`.",
            (
                f"- Main comparison: protocol `{summary['protocols']['baseline']}` "
                f"versus `{summary['protocols']['candidate']}` on the same 30 tasks."
            ),
            (
                "- The main comparison is regression evidence on a previously "
                "observed dataset, not a holdout benchmark."
            ),
            (
                "- Stability evidence consists of ten tasks run three times; the "
                "30 observations are clustered and are not 30 independent tasks."
            ),
            "",
            "## Main Regression Results",
            "",
            "| Metric | v1 | v2 | Change |",
            "| --- | ---: | ---: | ---: |",
            (
                f"| Completion | {main['baseline_completed']}/"
                f"{main['task_count']} | {main['candidate_completed']}/"
                f"{main['task_count']} | +{main['change_percentage_points']:.1f} pp |"
            ),
            (
                f"| Median latency | {median_latency['baseline'] / 1000:.1f}s | "
                f"{median_latency['candidate'] / 1000:.1f}s | "
                f"{median_latency['relative_change']:+.1%} |"
            ),
            (
                f"| P95 latency | {p95_latency['baseline'] / 1000:.1f}s | "
                f"{p95_latency['candidate'] / 1000:.1f}s | "
                f"{p95_latency['relative_change']:+.1%} |"
            ),
            (
                f"| Model cost | ${total_cost['baseline']:.4f} | "
                f"${total_cost['candidate']:.4f} | "
                f"{total_cost['relative_change']:+.1%} |"
            ),
            (
                f"| Cost per completed case | "
                f"${cost_per_completed['baseline']:.4f} | "
                f"${cost_per_completed['candidate']:.4f} | "
                f"{cost_per_completed['relative_change']:+.1%} |"
            ),
            (
                f"| Search calls | {efficiency['search_calls']['baseline']:.0f} | "
                f"{efficiency['search_calls']['candidate']:.0f} | "
                f"{efficiency['search_calls']['relative_change']:+.1%} |"
            ),
            "",
            (
                f"v2 improved {main['improved_case_count']} previous failures and "
                f"regressed {main['regressed_case_count']} previous successes. The "
                "higher completion rate came with increased latency and total model "
                "cost, while cost per completed case decreased."
            ),
            "",
            "## Repeated-Run Stability",
            "",
            (
                f"- Pooled completion: {stability['completed_observations']}/"
                f"{stability['observation_count']} "
                f"({_percent(stability['pooled_completion_rate'])})."
            ),
            (
                f"- Three-run completion agreement: "
                f"{_percent(stability['three_run_completion_agreement_rate'])}."
            ),
            (
                f"- Stable completed tasks: "
                f"{', '.join(stability['stable_completed_case_ids'])}."
            ),
            (
                f"- Stable incomplete tasks: "
                f"{', '.join(stability['stable_incomplete_case_ids'])}."
            ),
            (
                f"- Mixed-outcome tasks: "
                f"{', '.join(stability['mixed_outcome_case_ids'])}."
            ),
            (
                f"- Median within-task token CV: "
                f"{stability['median_within_task_token_cv']:.1%}; median within-task "
                f"latency CV: {stability['median_within_task_latency_cv']:.1%}."
            ),
            "",
            "## Cost Accounting",
            "",
            (
                f"The full v2 plan contained {cost['main_run_count']} main runs and "
                f"{cost['additional_stability_run_count']} additional stability "
                f"runs. After excluding the ten reused main traces, the "
                f"{cost['total_unique_paid_run_count']} unique paid runs cost "
                f"${cost['total_model_cost_usd']:.6f} and used "
                f"{cost['total_search_calls']} search calls."
            ),
            (
                f"The two additional stability rounds cost "
                f"${cost['additional_stability_model_cost_usd']:.6f}. Both the "
                "model-spend and search-call caps were respected."
            ),
            "",
            "## Failure Analysis",
            "",
            (
                "The remaining v2 main failures comprised "
                + ", ".join(
                    f"{count} {failure_type.replace('_', '-')} "
                    f"failure{'s' if count != 1 else ''}"
                    for failure_type, count in main[
                        "candidate_failure_type_counts"
                    ].items()
                )
                + "."
            ),
            (
                "Repeated runs show that artifact completion and control-flow "
                "termination remain variable: three subset tasks had mixed outcomes, "
                "and one task failed all three runs at the status level."
            ),
            "",
            "## Defensible Claims",
            "",
            *[f"- {claim}" for claim in summary["defensible_claims"]],
            "",
            "## Limitations",
            "",
            *[
                f"- The evidence does not establish that {claim[0].lower() + claim[1:]}"
                for claim in summary["unsupported_claims"]
            ],
            "- Stability statistics are descriptive because the subset contains only ten tasks and three runs per task.",
            (
                f"- Local token metrics were available for "
                f"{stability['token_observation_sample_count']}/"
                f"{stability['observation_count']} stability observations; "
                f"{stability['token_observation_missing_count']} terminal runs were "
                "excluded from token-variation statistics."
            ),
            "- Structural completion and source provenance do not independently verify factual correctness.",
            "",
        ]
    )


def publish_final_report(
    comparison_dir: Path,
    stability_dir: Path,
    output_dir: Path,
    *,
    generated_at: str | None = None,
) -> dict[str, Any]:
    if output_dir.exists():
        raise FileExistsError(f"final report output already exists: {output_dir}")
    summary = build_final_summary(
        comparison_dir,
        stability_dir,
        generated_at=generated_at,
    )
    output_dir.mkdir(parents=True)
    _write_json(output_dir / "summary.json", summary)
    (output_dir / "report.md").write_text(
        _render_report(summary),
        encoding="utf-8",
    )
    sources = {
        "comparison": {
            "path": _display_path(comparison_dir),
            "comparison_sha256": _sha256(comparison_dir / "comparison.json"),
            "manifest_sha256": _sha256(comparison_dir / "manifest.json"),
        },
        "stability": {
            "path": _display_path(stability_dir),
            "config_sha256": _sha256(stability_dir / "config.json"),
            "summary_sha256": _sha256(stability_dir / "summary.json"),
            "costs_sha256": _sha256(stability_dir / "costs.json"),
            "manifest_sha256": _sha256(stability_dir / "manifest.json"),
        },
    }
    manifest = {
        "schema_version": 1,
        "generated_at": summary["generated_at"],
        "sources": sources,
        "outputs": {
            "summary.json": _sha256(output_dir / "summary.json"),
            "report.md": _sha256(output_dir / "report.md"),
        },
    }
    _write_json(output_dir / "manifest.json", manifest)
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Publish the final Deep Research regression and stability report"
    )
    parser.add_argument(
        "--comparison-dir",
        default="evals/results/published/main_v1_vs_v2",
    )
    parser.add_argument(
        "--stability-dir",
        default="evals/results/published/stability_v2",
    )
    parser.add_argument(
        "--output-dir",
        default="evals/results/published/final_v2",
    )
    args = parser.parse_args()
    summary = publish_final_report(
        (PROJECT_ROOT / args.comparison_dir).resolve(),
        (PROJECT_ROOT / args.stability_dir).resolve(),
        (PROJECT_ROOT / args.output_dir).resolve(),
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
