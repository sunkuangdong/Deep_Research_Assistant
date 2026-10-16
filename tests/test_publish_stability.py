from __future__ import annotations

import json
from pathlib import Path

import pytest

from evals.publish_stability import (
    STABILITY_COMPATIBILITY_KEYS,
    publish_stability,
    validate_stability_preflight,
    validate_stability_subset,
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATASET = PROJECT_ROOT / "evals/datasets/research_main_v1.jsonl"
SUBSET = PROJECT_ROOT / "evals/stability_subset_v1.json"


def _write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload), encoding="utf-8")


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.write_text(
        "".join(json.dumps(row) + "\n" for row in rows),
        encoding="utf-8",
    )


def _runtime_config(*, commit: str, case_ids: list[str]) -> dict:
    values = {
        "protocol_version": "2.1.0",
        "dataset_version": "v1",
        "dataset_sha256": "9595213afcdd0b7baedf00f948d8364560e7484378ad06f88c0ed44d356fbf42",
        "provider": "openai",
        "model_name": "test-model",
        "model_base_url": "https://api.openai.com/v1",
        "model_max_input_tokens": 131072,
        "reasoning_effort": "none",
        "temperature": 0,
        "timeout_seconds": 900,
        "max_provider_retries": 2,
        "concurrency": 1,
        "deepagents_recursion_limit": 120,
        "search_call_limit": 6,
        "search_recovery_reserve": 1,
        "search_timeout_seconds": 20.0,
        "search_max_retries": 2,
        "fetch_call_limit": 6,
        "fetch_recovery_reserve": 1,
        "fetch_timeout_seconds": 20.0,
        "fetch_max_retries": 1,
        "fetch_max_bytes": 200000,
        "fetch_max_chars": 12000,
        "researcher_call_limit": 3,
        "researcher_initial_call_limit": 2,
        "researcher_recovery_call_limit": 1,
        "analyst_call_limit": 1,
        "editor_call_limit": 1,
        "draft_edit_call_limit": 1,
        "evidence_inventory_gate": True,
        "structured_research_plan_gate": True,
        "langfuse_tracing_enabled": True,
        "langfuse_environment": "evaluation",
        "langfuse_base_url": "https://us.cloud.langfuse.com",
        "run_date": "2026-10-16",
    }
    assert set(STABILITY_COMPATIBILITY_KEYS) <= set(values)
    values["git_commit"] = commit
    values["selected_case_ids"] = case_ids
    return values


def _published_main_run(case_id: str, index: int) -> dict:
    return {
        "case_id": case_id,
        "category": "test",
        "language": "en",
        "source_result_dir": "main-source",
        "status": "completed",
        "failure_type": None,
        "original_status": "completed",
        "original_failure_type": None,
        "rescored": True,
        "status_changed_by_rescore": False,
        "langfuse_trace_id": f"main-{case_id}",
        "latency_ms": 1000 + index,
        "usage": {
            "llm_calls": 2,
            "input_tokens": 100,
            "output_tokens": 20,
            "total_tokens": 120 + index,
        },
        "calls": {
            "llm_calls": 2,
            "search_calls": 2,
            "fetch_calls": 1,
            "researcher_calls": 2,
            "analyst_calls": 1,
            "editor_calls": 1,
            "draft_edit_calls": 1,
        },
        "score": {"completed": True, "artifact_completeness": 1},
        "published_report": None,
    }


def _raw_repeat_run(
    case_id: str,
    index: int,
    *,
    repeat_index: int,
    completed: bool,
) -> dict:
    status = "completed" if completed else "agent_failure"
    failure_type = None if completed else "acceptance_criteria"
    return {
        "case_id": case_id,
        "started_at": f"2026-10-16T00:{index:02d}:00+00:00",
        "finished_at": f"2026-10-16T00:{index:02d}:01+00:00",
        "status": status,
        "failure_type": failure_type,
        "langfuse_trace_id": f"repeat-{repeat_index}-{case_id}",
        "latency_ms": 1100 + index + repeat_index,
        "metadata": {
            "usage": {
                "llm_calls": 2,
                "input_tokens": 110,
                "output_tokens": 21,
                "total_tokens": 130 + index + repeat_index,
            },
            "search_calls": 2,
            "fetch_calls": 1,
            "researcher_calls": 2,
            "analyst_calls": 1,
            "editor_calls": 1,
            "draft_edit_calls": 1,
        },
        "score": {
            "completed": completed,
            "artifact_completeness": 1 if completed else 0.5,
        },
    }


def _evaluation_tree(tmp_path: Path) -> tuple[Path, list[Path], list[str]]:
    subset_validation = validate_stability_subset(DATASET, SUBSET)
    case_ids = subset_validation["case_ids"]
    results_root = tmp_path / "results"
    main_source = results_root / "main-source"
    main_source.mkdir(parents=True)
    _write_json(
        main_source / "config.json",
        _runtime_config(commit="main-commit", case_ids=case_ids),
    )
    _write_jsonl(main_source / "raw_runs.jsonl", [])

    main_bundle = results_root / "published/main_v2"
    main_bundle.mkdir(parents=True)
    main_config = _runtime_config(commit="main-commit", case_ids=case_ids)
    main_config.update(
        {
            "dataset_name": "research_main_v1",
            "source_git_commits": ["main-commit"],
        }
    )
    _write_json(main_bundle / "config.json", main_config)
    _write_jsonl(
        main_bundle / "rescored_runs.jsonl",
        [_published_main_run(case_id, index) for index, case_id in enumerate(case_ids)],
    )

    repeat_dirs: list[Path] = []
    for repeat_index in (2, 3):
        repeat_dir = results_root / f"stability-round-{repeat_index}"
        repeat_dir.mkdir()
        _write_json(
            repeat_dir / "config.json",
            _runtime_config(commit=f"repeat-{repeat_index}", case_ids=case_ids),
        )
        rows = [
            _raw_repeat_run(
                case_id,
                index,
                repeat_index=repeat_index,
                completed=not (repeat_index == 3 and index == 0),
            )
            for index, case_id in enumerate(case_ids)
        ]
        _write_jsonl(repeat_dir / "raw_runs.jsonl", rows)
        repeat_dirs.append(repeat_dir)
    return main_bundle, repeat_dirs, case_ids


def test_frozen_stability_subset_matches_main_dataset():
    validation = validate_stability_subset(DATASET, SUBSET)

    assert validation["valid"] is True
    assert len(validation["case_ids"]) == 10
    assert validation["strata"]["languages"] == {"en": 5, "zh": 5}
    assert validation["strata"]["analysis_requirement"] == {
        "analysis": 8,
        "no_analysis": 2,
    }


def test_publish_stability_preserves_three_observations_per_case(tmp_path: Path):
    main_bundle, repeat_dirs, case_ids = _evaluation_tree(tmp_path)
    output_dir = tmp_path / "published-stability"
    raw_before = [
        (repeat_dir / "raw_runs.jsonl").read_bytes() for repeat_dir in repeat_dirs
    ]

    summary = publish_stability(
        DATASET,
        SUBSET,
        main_bundle,
        repeat_dirs,
        output_dir,
        published_at="2026-10-16T00:00:00+00:00",
    )

    assert summary["task_count"] == 10
    assert summary["observation_count"] == 30
    assert summary["completed_observation_count"] == 29
    assert summary["completion_agreement"]["all_three_agree_count"] == 9
    assert summary["completion_agreement"]["mixed_outcome_count"] == 1
    first = summary["per_task"][0]
    assert first["case_id"] == case_ids[0]
    assert first["completed_runs"] == 2
    assert first["completion_agreement"] is False
    published_rows = [
        json.loads(line)
        for line in (output_dir / "rescored_runs.jsonl")
        .read_text(encoding="utf-8")
        .splitlines()
    ]
    assert len(published_rows) == 30
    assert sorted(
        row["repeat_index"] for row in published_rows if row["case_id"] == case_ids[0]
    ) == [1, 2, 3]
    assert (output_dir / "manifest.json").is_file()
    assert "not holdout evidence" in (output_dir / "report.md").read_text(
        encoding="utf-8"
    )
    assert raw_before == [
        (repeat_dir / "raw_runs.jsonl").read_bytes() for repeat_dir in repeat_dirs
    ]


def test_stability_preflight_validates_published_main_observations(tmp_path: Path):
    main_bundle, _repeat_dirs, case_ids = _evaluation_tree(tmp_path)

    preflight = validate_stability_preflight(DATASET, SUBSET, main_bundle)

    assert preflight["valid"] is True
    assert preflight["case_ids"] == case_ids
    assert preflight["main_observation_status_counts"] == {"completed": 10}
    assert preflight["main_source_git_commits"] == ["main-commit"]


def test_publish_stability_rejects_runtime_mismatch(tmp_path: Path):
    main_bundle, repeat_dirs, _case_ids = _evaluation_tree(tmp_path)
    config_path = repeat_dirs[1] / "config.json"
    config = json.loads(config_path.read_text(encoding="utf-8"))
    config["model_name"] = "different-model"
    _write_json(config_path, config)

    with pytest.raises(ValueError, match="model_name"):
        publish_stability(
            DATASET,
            SUBSET,
            main_bundle,
            repeat_dirs,
            tmp_path / "output",
        )
