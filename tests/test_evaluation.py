import asyncio
import json
from pathlib import Path

import evals.run_deep_research as eval_runner
from evals.runtime_config import sanitize_base_url
from evals.scoring import score_workspace
from evals.validation import validate_suite


def test_evaluation_datasets_are_valid_and_disjoint():
    result = validate_suite(Path("evals/datasets"))

    assert result["valid"], result["errors"]
    assert [item["case_count"] for item in result["datasets"]] == [6, 30]


def test_scoring_accepts_complete_workspace(tmp_path: Path):
    sources = tmp_path / "sources"
    reports = tmp_path / "reports"
    sources.mkdir()
    reports.mkdir()
    (sources / "question.txt").write_text("question", encoding="utf-8")
    (sources / "research_plan.md").write_text("plan", encoding="utf-8")
    (sources / "findings_test.md").write_text("findings", encoding="utf-8")
    (sources / "analysis_test.md").write_text("analysis", encoding="utf-8")
    (reports / "draft_test.md").write_text("draft", encoding="utf-8")
    (reports / "report_test.md").write_text(
        "## Background\nhttps://one.example\n\n"
        "## Key Findings\nhttps://two.example\n\n"
        "## Recommendations\nhttps://three.example\n",
        encoding="utf-8",
    )
    case = {
        "required_artifacts": [
            "question",
            "research_plan",
            "findings",
            "analysis",
            "draft",
            "report",
        ],
        "required_sections": ["Background", "Key Findings", "Recommendations"],
        "minimum_citations": 3,
    }
    metadata = {
        "search_calls": 2,
        "search_call_limit": 6,
        "analyst_calls": 1,
        "analyst_call_limit": 1,
        "editor_calls": 1,
        "editor_call_limit": 1,
    }

    score = score_workspace(tmp_path, case, metadata)

    assert score["completed"] is True
    assert score["artifact_completeness"] == 1
    assert score["citation_count"] == 3


def test_scoring_rejects_missing_section_and_budget_violation(tmp_path: Path):
    (tmp_path / "reports").mkdir()
    (tmp_path / "reports/report_test.md").write_text(
        "## Background\nhttps://one.example\n", encoding="utf-8"
    )
    case = {
        "required_artifacts": ["report"],
        "required_sections": ["Background", "Limitations"],
        "minimum_citations": 1,
    }
    metadata = {
        "search_calls": 7,
        "search_call_limit": 6,
        "analyst_calls": 0,
        "analyst_call_limit": 1,
        "editor_calls": 0,
        "editor_call_limit": 1,
    }

    score = score_workspace(tmp_path, case, metadata)

    assert score["completed"] is False
    assert score["missing_sections"] == ["Limitations"]
    assert score["budget_checks"]["search"] is False


def test_base_url_capture_strips_credentials_and_query():
    sanitized = sanitize_base_url(
        "https://user:secret@example.com:8443/v1?api_key=secret#fragment"
    )

    assert sanitized == "https://example.com:8443/v1"
    assert "secret" not in sanitized


def test_runner_records_timeout_without_retrying_agent_failure(
    tmp_path: Path, monkeypatch
):
    async def slow_workflow(*_args, **_kwargs):
        await asyncio.sleep(0.1)

    monkeypatch.setattr(eval_runner, "run_deepagents_workflow", slow_workflow)
    case = {
        "id": "timeout-case",
        "language": "en",
        "topic": "Timeout fixture",
        "no_analysis": True,
        "required_artifacts": ["report"],
        "required_sections": ["Summary"],
        "minimum_citations": 1,
    }

    result = asyncio.run(eval_runner._run_case(case, tmp_path, 0.01))

    assert result["status"] == "infrastructure_failure"
    assert result["failure_type"] == "timeout"
    assert result["latency_ms"] >= 0


def test_smoke_dataset_is_valid_jsonl():
    rows = [
        json.loads(line)
        for line in Path("evals/datasets/research_smoke_v1.jsonl")
        .read_text(encoding="utf-8")
        .splitlines()
        if line.strip()
    ]

    assert len(rows) == 6
