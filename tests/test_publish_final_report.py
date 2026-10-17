from __future__ import annotations

import json
from pathlib import Path

import pytest

from evals.publish_final_report import build_final_summary, publish_final_report


def _write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload), encoding="utf-8")


def _evidence_tree(tmp_path: Path) -> tuple[Path, Path]:
    comparison_dir = tmp_path / "comparison"
    stability_dir = tmp_path / "stability"
    comparison_dir.mkdir()
    stability_dir.mkdir()
    _write_json(
        comparison_dir / "comparison.json",
        {
            "comparison_type": "regression_on_previously_observed_dataset",
            "baseline": {
                "protocol_version": "1.0",
                "dataset_sha256": "dataset-hash",
                "model_name": "model-a",
            },
            "candidate": {
                "protocol_version": "2.0",
                "dataset_sha256": "dataset-hash",
                "model_name": "model-a",
            },
            "completion": {
                "run_count": 30,
                "baseline_completed": 10,
                "candidate_completed": 24,
                "baseline_rate": 1 / 3,
                "candidate_rate": 0.8,
                "change_percentage_points": 46.666667,
            },
            "transitions": {"counts": {"improved": 16, "regressed": 2}},
            "candidate_status_counts": {
                "completed": 24,
                "agent_failure": 6,
                "infrastructure_failure": 0,
            },
            "candidate_failure_type_counts": {"acceptance_criteria": 6},
            "efficiency": {
                "latency_ms": {
                    "median": {
                        "baseline": 100000,
                        "candidate": 120000,
                        "relative_change": 0.2,
                    },
                    "p95_nearest_rank": {
                        "baseline": 200000,
                        "candidate": 260000,
                        "relative_change": 0.3,
                    },
                },
                "model_cost_usd": {
                    "total": {
                        "baseline": 0.5,
                        "candidate": 0.7,
                        "relative_change": 0.4,
                    },
                    "cost_per_completed_case": {
                        "baseline": 0.05,
                        "candidate": 0.0291667,
                        "relative_change": -0.416666,
                    },
                },
                "bocha_search": {
                    "calls": {
                        "baseline": 180,
                        "candidate": 160,
                        "relative_change": -0.111111,
                    }
                },
            },
        },
    )
    _write_json(comparison_dir / "manifest.json", {})
    _write_json(
        stability_dir / "config.json",
        {
            "protocol_version": "2.0",
            "dataset_sha256": "dataset-hash",
            "model_name": "model-a",
            "repeat_count": 3,
        },
    )
    per_task = []
    for index in range(10):
        completed_runs = 3 if index < 6 else (0 if index == 6 else 2)
        per_task.append(
            {
                "case_id": f"case-{index}",
                "completed_runs": completed_runs,
                "completion_agreement": completed_runs in {0, 3},
                "tokens": {"coefficient_of_variation": 0.1 + index / 100},
                "latency_ms": {"coefficient_of_variation": 0.2 + index / 100},
            }
        )
    _write_json(
        stability_dir / "summary.json",
        {
            "task_count": 10,
            "repeat_count": 3,
            "observation_count": 30,
            "completed_observation_count": 24,
            "pooled_completion_rate": 0.8,
            "completion_agreement": {
                "rate": 0.7,
                "frequency_distribution": {
                    "0/3": 1,
                    "1/3": 0,
                    "2/3": 3,
                    "3/3": 6,
                },
            },
            "exact_status_agreement": {"rate": 0.7},
            "tokens": {"sample_count": 28, "missing_count": 2},
            "latency_ms": {"sample_count": 30, "missing_count": 0},
            "per_task": per_task,
        },
    )
    _write_json(
        stability_dir / "costs.json",
        {
            "stability_cost": {
                "additional_stability_runs": {
                    "run_count": 20,
                    "model_cost_usd": 0.4,
                    "search_calls": 100,
                },
                "full_v2_experiment": {
                    "main_run_count": 30,
                    "additional_stability_run_count": 20,
                    "total_unique_paid_run_count": 50,
                    "model_cost_usd": 1.1,
                    "search_calls": 260,
                    "within_model_spend_cap": True,
                    "within_search_call_cap": True,
                },
            }
        },
    )
    _write_json(stability_dir / "manifest.json", {})
    return comparison_dir, stability_dir


def test_publish_final_report_combines_regression_and_stability(tmp_path: Path):
    comparison_dir, stability_dir = _evidence_tree(tmp_path)
    output_dir = tmp_path / "final"

    summary = publish_final_report(
        comparison_dir,
        stability_dir,
        output_dir,
        generated_at="2026-10-16T00:00:00+00:00",
    )

    assert summary["main_regression"]["candidate_completion_rate"] == 0.8
    assert summary["stability"]["three_run_completion_agreement_rate"] == 0.7
    assert len(summary["stability"]["stable_completed_case_ids"]) == 6
    assert len(summary["stability"]["mixed_outcome_case_ids"]) == 3
    assert (
        summary["deduplicated_v2_experiment_cost"]["total_unique_paid_run_count"] == 50
    )
    report = (output_dir / "report.md").read_text(encoding="utf-8")
    assert "not a holdout benchmark" in report
    assert "50 unique paid runs" in report
    assert "does not establish that the 80.0% completion rate generalizes" in report
    assert "28/30 stability observations" in report
    assert "6 acceptance-criteria failures" in report
    assert (output_dir / "manifest.json").is_file()


def test_build_final_summary_rejects_incompatible_model(tmp_path: Path):
    comparison_dir, stability_dir = _evidence_tree(tmp_path)
    config_path = stability_dir / "config.json"
    config = json.loads(config_path.read_text())
    config["model_name"] = "different-model"
    _write_json(config_path, config)

    with pytest.raises(ValueError, match="model_name"):
        build_final_summary(comparison_dir, stability_dir)
