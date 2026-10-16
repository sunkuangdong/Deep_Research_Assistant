from __future__ import annotations

import json
from pathlib import Path

from evals.analyze_failures import (
    analyze_published_failures,
    build_failure_analysis,
    classify_failure,
)


def _run(
    case_id: str,
    *,
    status: str = "agent_failure",
    citation_count: int = 5,
    minimum_citations: int = 5,
    missing_artifacts: list[str] | None = None,
    retrieved_in_run: bool = True,
    evidence_provenance: bool = True,
) -> dict:
    missing = missing_artifacts or []
    report_files = [] if "report" in missing else ["reports/report_test.md"]
    return {
        "case_id": case_id,
        "category": "test",
        "language": "en",
        "status": status,
        "failure_type": None if status == "completed" else "acceptance_criteria",
        "score": {
            "artifact_completeness": 0.5 if missing else 1.0,
            "artifact_files": {"report": report_files},
            "missing_artifacts": missing,
            "invalid_artifact_paths": [],
            "missing_sections": [],
            "citation_count": citation_count,
            "minimum_citations": minimum_citations,
            "invalid_citations": [],
            "citations_not_retrieved": (
                [] if retrieved_in_run else ["https://example.com/not-retrieved"]
            ),
            "citations_without_evidence": (
                [] if evidence_provenance else ["https://example.com/no-evidence"]
            ),
            "source_link_checks": {
                "syntax": True,
                "retrieved_in_run": retrieved_in_run,
                "evidence_provenance": evidence_provenance,
            },
            "language_compliance": True,
            "budget_checks": {"search": True},
            "report_date_compliance": True,
        },
    }


def test_classify_failure_avoids_derivative_citation_failure_without_report():
    run = _run(
        "case-workflow",
        citation_count=0,
        minimum_citations=5,
        missing_artifacts=["draft", "report"],
    )
    assert classify_failure(run) == ["workflow_incomplete"]


def test_build_failure_analysis_counts_overlapping_evidence_failures():
    runs = [
        _run("case-pass", status="completed"),
        _run("case-citations", citation_count=3),
        _run(
            "case-links",
            retrieved_in_run=False,
            evidence_provenance=False,
        ),
        _run("case-workflow", missing_artifacts=["report"]),
    ]
    analysis = build_failure_analysis(
        runs,
        source_bundle="main_v1",
        generated_at="2026-10-16T00:00:00+00:00",
    )

    assert analysis["run_count"] == 4
    assert analysis["failed_count"] == 3
    dimensions = {
        item["dimension"]: item["case_count"]
        for item in analysis["dimension_counts"]
    }
    assert dimensions == {
        "citation_shortfall": 1,
        "evidence_provenance": 1,
        "source_not_retrieved": 1,
        "workflow_incomplete": 1,
    }
    priorities = {
        item["change_id"]: item for item in analysis["change_priorities"]
    }
    assert priorities["evidence_inventory_gate"]["potential_coverage_count"] == 2
    assert priorities["phase_state_machine_finalizer"][
        "potential_coverage_count"
    ] == 1


def test_analyze_published_failures_writes_report_and_updates_manifest(
    tmp_path: Path,
):
    published = tmp_path / "main_v1"
    published.mkdir()
    runs = [
        _run("case-pass", status="completed"),
        _run("case-fail", citation_count=4),
    ]
    (published / "rescored_runs.jsonl").write_text(
        "".join(json.dumps(run) + "\n" for run in runs), encoding="utf-8"
    )
    (published / "manifest.json").write_text("{}\n", encoding="utf-8")

    analysis = analyze_published_failures(
        published,
        generated_at="2026-10-16T00:00:00+00:00",
    )

    assert analysis["failed_count"] == 1
    assert (published / "failure_analysis.json").is_file()
    report = (published / "failure_analysis.md").read_text(encoding="utf-8")
    assert report.startswith("# Deep Research Main Benchmark Failure Analysis\n")
    assert "Potential coverage: 1/1 observed failures" in report
    manifest = json.loads(
        (published / "manifest.json").read_text(encoding="utf-8")
    )
    assert len(manifest["failure_analysis"]["json_sha256"]) == 64
    assert len(manifest["failure_analysis"]["markdown_sha256"]) == 64
