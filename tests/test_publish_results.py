from __future__ import annotations

import hashlib
import json
from pathlib import Path

from evals.publish_results import _report_profile, publish_results


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_publish_results_rescores_without_mutating_raw_run(tmp_path: Path):
    dataset = tmp_path / "research_smoke_v1.jsonl"
    case = {
        "id": "dr-smoke-001",
        "language": "en",
        "category": "test",
        "topic": "Test publishing",
        "no_analysis": True,
        "required_artifacts": ["findings", "report"],
        "required_sections": ["Background"],
        "minimum_citations": 1,
    }
    dataset.write_text(json.dumps(case) + "\n", encoding="utf-8")
    results_root = tmp_path / "results"
    result_dir = results_root / "20261014T000000Z_model_research_smoke_v1"
    workspace = result_dir / "workspaces/dr-smoke-001/workspace"
    (workspace / "sources").mkdir(parents=True)
    (workspace / "reports").mkdir()
    citation = "https://developer.mozilla.org/en-US/docs/Web/API/Response/body"
    (workspace / "sources/findings_test.md").write_text(
        f"English evidence stored as `{citation}`.", encoding="utf-8"
    )
    (workspace / "reports/report_test_2026-10-14.md").write_text(
        f"## Background\nEnglish report cites [MDN]({citation}).\n",
        encoding="utf-8",
    )
    config = {
        "protocol_version": "1.3.0-draft",
        "dataset_version": "v1",
        "dataset_sha256": _sha256(dataset),
        "git_commit": "test-commit",
        "provider": "openai",
        "model_name": "test-model",
        "model_base_url": "https://api.openai.com/v1",
        "model_max_input_tokens": 1000,
        "reasoning_effort": "none",
        "temperature": 0,
        "timeout_seconds": 900,
        "max_provider_retries": 2,
        "concurrency": 1,
        "deepagents_recursion_limit": 120,
        "search_call_limit": 6,
        "search_timeout_seconds": 20,
        "search_max_retries": 2,
        "fetch_call_limit": 6,
        "fetch_timeout_seconds": 20,
        "fetch_max_retries": 1,
        "fetch_max_bytes": 200000,
        "fetch_max_chars": 12000,
        "researcher_call_limit": 3,
        "analyst_call_limit": 1,
        "editor_call_limit": 1,
        "draft_edit_call_limit": 1,
        "run_date": "2026-10-14",
    }
    (result_dir / "config.json").write_text(
        json.dumps(config), encoding="utf-8"
    )
    metadata = {
        "run_date": "2026-10-14",
        "usage": {
            "llm_calls": 2,
            "input_tokens": 100,
            "output_tokens": 20,
            "total_tokens": 120,
        },
        "retrieved_source_urls": [citation],
        "search_calls": 1,
        "search_call_limit": 6,
        "fetch_calls": 1,
        "fetch_call_limit": 6,
        "researcher_calls": 1,
        "researcher_call_limit": 3,
        "analyst_calls": 0,
        "analyst_call_limit": 1,
        "editor_calls": 1,
        "editor_call_limit": 1,
        "draft_edit_calls": 0,
        "draft_edit_call_limit": 1,
    }
    raw = {
        "case_id": case["id"],
        "started_at": "2026-10-14T00:00:00+00:00",
        "finished_at": "2026-10-14T00:00:01+00:00",
        "status": "agent_failure",
        "failure_type": "acceptance_criteria",
        "langfuse_trace_id": "trace-test",
        "final_text": "English final response with sufficient content for validation.",
        "metadata": metadata,
        "score": {"completed": False},
        "latency_ms": 1000,
    }
    raw_path = result_dir / "raw_runs.jsonl"
    original_raw = json.dumps(raw) + "\n"
    raw_path.write_text(original_raw, encoding="utf-8")

    output_dir = results_root / "published/smoke_v1"
    summary = publish_results(dataset, results_root, output_dir)

    published = json.loads(
        (output_dir / "rescored_runs.jsonl").read_text(encoding="utf-8")
    )
    assert published["original_status"] == "agent_failure"
    assert published["status"] == "completed"
    assert published["status_changed_by_rescore"] is True
    assert published["score"]["citations_without_evidence"] == []
    assert summary["completion_rate"] == 1
    assert summary["tokens"]["median"] == 120
    assert (output_dir / "reports/dr-smoke-001.md").is_file()
    assert (output_dir / "manifest.json").is_file()
    report = (output_dir / "report.md").read_text(encoding="utf-8")
    assert report.startswith("# Published Deep Research Smoke Evaluation\n")
    assert "Smoke metrics validate the harness" in report
    assert raw_path.read_text(encoding="utf-8") == original_raw


def test_report_profile_distinguishes_main_benchmark_from_smoke():
    assert _report_profile("research_main_v1") == (
        "Main Benchmark",
        "Main benchmark metrics include every fixed case selected under the frozen protocol.",
    )
