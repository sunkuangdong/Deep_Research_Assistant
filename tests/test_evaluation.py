import asyncio
import json
from contextlib import contextmanager
from pathlib import Path

import pytest

import evals.run_deep_research as eval_runner
from evals.langfuse_observability import CaseTrace, validate_langfuse_config
from evals.runtime_config import sanitize_base_url
from evals.scoring import score_workspace
from evals.validation import validate_suite
from src.workflow.deepagents_runner import DeepAgentsRunResult


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


def test_langfuse_disabled_does_not_require_credentials(monkeypatch):
    monkeypatch.setenv("LANGFUSE_TRACING_ENABLED", "false")
    monkeypatch.delenv("LANGFUSE_PUBLIC_KEY", raising=False)
    monkeypatch.delenv("LANGFUSE_SECRET_KEY", raising=False)
    monkeypatch.delenv("LANGFUSE_BASE_URL", raising=False)

    assert validate_langfuse_config() is False


def test_langfuse_enabled_requires_credentials(monkeypatch):
    monkeypatch.setenv("LANGFUSE_TRACING_ENABLED", "true")
    monkeypatch.delenv("LANGFUSE_PUBLIC_KEY", raising=False)
    monkeypatch.delenv("LANGFUSE_SECRET_KEY", raising=False)
    monkeypatch.delenv("LANGFUSE_BASE_URL", raising=False)

    with pytest.raises(ValueError, match="LANGFUSE_PUBLIC_KEY"):
        validate_langfuse_config()


def test_case_trace_mirrors_local_deterministic_scores():
    class FakeSpan:
        def __init__(self):
            self.output = None
            self.scores = []

        def update(self, *, output):
            self.output = output

        def score_trace(self, **score):
            self.scores.append(score)

    span = FakeSpan()
    trace = CaseTrace(trace_id="trace-123", span=span)
    trace.record_result(
        {
            "status": "completed",
            "failure_type": None,
            "latency_ms": 123,
            "metadata": {"usage": {"total_tokens": 456}},
            "score": {
                "artifact_completeness": 1,
                "citation_count": 5,
                "budget_checks": {
                    "search": True,
                    "analyst": True,
                    "editor": False,
                },
            },
        }
    )

    scores = {item["name"]: item["value"] for item in span.scores}
    assert span.output["usage"]["total_tokens"] == 456
    assert scores == {
        "completed": 1,
        "artifact_completeness": 1.0,
        "citation_count": 5.0,
        "search_budget_compliance": 1,
        "analyst_budget_compliance": 1,
        "editor_budget_compliance": 0,
    }


def test_runner_passes_trace_callback_and_records_trace_id(tmp_path, monkeypatch):
    callback = object()
    captured = {}

    @contextmanager
    def fake_start_case_trace(**kwargs):
        captured["trace_kwargs"] = kwargs
        yield CaseTrace(callbacks=[callback], trace_id="trace-123")

    async def fake_workflow(*_args, **kwargs):
        captured["callbacks"] = kwargs["callbacks"]
        return DeepAgentsRunResult(
            final_text="done",
            metadata={
                "usage": {"total_tokens": 10},
                "search_calls": 1,
                "search_call_limit": 6,
                "analyst_calls": 0,
                "analyst_call_limit": 1,
                "editor_calls": 1,
                "editor_call_limit": 1,
            },
        )

    monkeypatch.setattr(eval_runner, "start_case_trace", fake_start_case_trace)
    monkeypatch.setattr(eval_runner, "run_deepagents_workflow", fake_workflow)
    monkeypatch.setattr(
        eval_runner,
        "score_workspace",
        lambda *_args: {
            "completed": True,
            "artifact_completeness": 1,
            "citation_count": 3,
            "budget_checks": {"search": True, "analyst": True, "editor": True},
        },
    )
    case = {
        "id": "trace-case",
        "language": "en",
        "topic": "Trace fixture",
        "no_analysis": True,
        "required_artifacts": ["report"],
        "required_sections": ["Summary"],
        "minimum_citations": 1,
    }

    result = asyncio.run(
        eval_runner._run_case(
            case,
            tmp_path,
            1,
            trace_metadata={"dataset_version": "v1"},
            trace_session_id="test-session",
        )
    )

    assert captured["callbacks"] == [callback]
    assert captured["trace_kwargs"]["session_id"] == "test-session"
    assert result["langfuse_trace_id"] == "trace-123"
    assert result["status"] == "completed"
