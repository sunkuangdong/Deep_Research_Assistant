from __future__ import annotations

import json
from pathlib import Path

import pytest

from evals.compare_results import build_comparison, write_comparison


def _write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload), encoding="utf-8")


def _bundle(
    root: Path,
    name: str,
    *,
    protocol: str,
    statuses: list[str],
    cost: float,
    latency: tuple[float, float, float],
) -> Path:
    bundle = root / "published" / name
    bundle.mkdir(parents=True)
    runs = []
    for index, status in enumerate(statuses, start=1):
        case_id = f"case-{index}"
        failure_type = None if status == "completed" else "acceptance_criteria"
        runs.append(
            {
                "case_id": case_id,
                "status": status,
                "failure_type": failure_type,
                "source_result_dir": f"source-{name}",
                "score": {
                    "artifact_completeness": 1 if status == "completed" else 0.5,
                    "language_compliance": True,
                    "citation_count": 5 if status == "completed" else 3,
                    "minimum_citations": 5,
                },
            }
        )
    (bundle / "rescored_runs.jsonl").write_text(
        "".join(json.dumps(run) + "\n" for run in runs),
        encoding="utf-8",
    )
    completed = statuses.count("completed")
    _write_json(
        bundle / "config.json",
        {
            "protocol_version": protocol,
            "dataset_sha256": "dataset-hash",
            "model_name": "model-a",
            "source_git_commits": [f"commit-{protocol}"],
        },
    )
    _write_json(
        bundle / "summary.json",
        {
            "run_count": len(statuses),
            "completed_count": completed,
            "completion_rate": completed / len(statuses),
            "status_counts": {
                "completed": completed,
                "agent_failure": len(statuses) - completed,
                "infrastructure_failure": 0,
            },
            "artifact_completeness_rate": 0.75,
            "language_compliance_rate": 1.0,
            "budget_compliance_rate": 1.0,
            "source_link_compliance_rate": 0.75,
            "tokens": {
                "sample_count": len(statuses),
                "median": 100,
                "p95_nearest_rank": 150,
            },
            "latency_ms": {
                "mean": latency[0],
                "median": latency[1],
                "p95_nearest_rank": latency[2],
            },
        },
    )
    _write_json(
        bundle / "costs.json",
        {
            "validation": {
                "trace_count": len(statuses),
                "all_generations_priced": True,
            },
            "model_cost": {
                "total_usd": cost,
                "mean_per_run_usd": cost / len(statuses),
            },
            "bocha_search_cost": {
                "evaluation_search_calls": 10,
                "evaluation_allocated_cost_cny": 0.036,
            },
        },
    )
    return bundle


def test_write_comparison_reports_status_and_cost_tradeoffs(tmp_path: Path):
    baseline = _bundle(
        tmp_path,
        "v1",
        protocol="1.0",
        statuses=["completed", "agent_failure"],
        cost=0.04,
        latency=(100, 100, 120),
    )
    candidate = _bundle(
        tmp_path,
        "v2",
        protocol="2.0",
        statuses=["completed", "completed"],
        cost=0.06,
        latency=(150, 150, 180),
    )
    output = tmp_path / "comparison"

    comparison = write_comparison(
        baseline,
        candidate,
        output,
        generated_at="2026-10-16T00:00:00+00:00",
    )

    assert comparison["comparison_type"] == (
        "regression_on_previously_observed_dataset"
    )
    assert comparison["completion"]["change_percentage_points"] == 50
    assert comparison["transitions"]["counts"]["improved"] == 1
    assert comparison["efficiency"]["model_cost_usd"]["total"]["relative_change"] == 0.5
    assert (
        comparison["efficiency"]["model_cost_usd"]["cost_per_completed_case"][
            "relative_change"
        ]
        == -0.25
    )
    assert (output / "comparison.json").is_file()
    assert (output / "manifest.json").is_file()
    report = (output / "report.md").read_text(encoding="utf-8")
    assert "not a holdout benchmark" in report
    assert "50.0 pp" in report


def test_build_comparison_rejects_dataset_mismatch(tmp_path: Path):
    baseline = _bundle(
        tmp_path,
        "v1",
        protocol="1.0",
        statuses=["completed"],
        cost=0.01,
        latency=(100, 100, 100),
    )
    candidate = _bundle(
        tmp_path,
        "v2",
        protocol="2.0",
        statuses=["completed"],
        cost=0.01,
        latency=(100, 100, 100),
    )
    config_path = candidate / "config.json"
    config = json.loads(config_path.read_text(encoding="utf-8"))
    config["dataset_sha256"] = "different"
    _write_json(config_path, config)

    with pytest.raises(ValueError, match="dataset_sha256"):
        build_comparison(baseline, candidate)
