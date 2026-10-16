from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter, defaultdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]

DIMENSION_LABELS = {
    "workflow_incomplete": "Workflow stopped before required artifacts were complete",
    "citation_shortfall": "Final report did not meet the minimum citation count",
    "source_not_retrieved": "Final report cited a URL not retrieved in the run",
    "evidence_provenance": "Final report cited a URL absent from findings or analysis",
    "invalid_citation": "Final report contained an invalid citation URL",
    "missing_sections": "Final report omitted required sections",
    "language_noncompliance": "Artifacts or final response violated the language policy",
    "budget_noncompliance": "One or more execution budgets were exceeded",
    "report_date_noncompliance": "Final report filename used the wrong run date",
    "infrastructure_failure": "Provider or runtime infrastructure failed",
    "unclassified": "Failure was not explained by a known acceptance dimension",
}


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


def _failed_checks(checks: dict[str, Any] | None) -> list[str]:
    return sorted(key for key, value in (checks or {}).items() if not value)


def classify_failure(run: dict[str, Any]) -> list[str]:
    if run.get("status") == "infrastructure_failure":
        return ["infrastructure_failure"]

    score = run.get("score") or {}
    dimensions: list[str] = []
    missing_artifacts = score.get("missing_artifacts") or []
    invalid_paths = score.get("invalid_artifact_paths") or []
    artifact_incomplete = float(score.get("artifact_completeness") or 0) < 1
    report_files = (score.get("artifact_files") or {}).get("report") or []
    report_exists = bool(report_files) and "report" not in missing_artifacts

    if artifact_incomplete or missing_artifacts or invalid_paths:
        dimensions.append("workflow_incomplete")

    # Missing reports mechanically have zero citations and all sections missing.
    # Treat those as consequences of workflow termination, not separate root causes.
    if report_exists:
        citation_count = int(score.get("citation_count") or 0)
        minimum_citations = int(score.get("minimum_citations") or 0)
        if citation_count < minimum_citations:
            dimensions.append("citation_shortfall")
        if score.get("invalid_citations"):
            dimensions.append("invalid_citation")
        if score.get("missing_sections"):
            dimensions.append("missing_sections")

        source_checks = score.get("source_link_checks") or {}
        if (
            source_checks.get("retrieved_in_run") is False
            or score.get("citations_not_retrieved")
        ):
            dimensions.append("source_not_retrieved")
        if (
            source_checks.get("evidence_provenance") is False
            or score.get("citations_without_evidence")
        ):
            dimensions.append("evidence_provenance")

    if score.get("language_compliance") is False:
        dimensions.append("language_noncompliance")
    if _failed_checks(score.get("budget_checks")):
        dimensions.append("budget_noncompliance")
    if score.get("report_date_compliance") is False:
        dimensions.append("report_date_noncompliance")

    return dimensions or ["unclassified"]


def _group_summary(
    runs: list[dict[str, Any]],
    field: str,
) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for run in runs:
        grouped[str(run.get(field) or "unknown")].append(run)
    return [
        {
            field: name,
            "run_count": len(items),
            "completed_count": sum(item.get("status") == "completed" for item in items),
            "completion_rate": round(
                sum(item.get("status") == "completed" for item in items) / len(items),
                4,
            ),
        }
        for name, items in sorted(grouped.items())
    ]


def _change_priorities(
    failures: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    cases_by_dimension = {
        dimension: {
            failure["case_id"]
            for failure in failures
            if dimension in failure["failure_dimensions"]
        }
        for dimension in DIMENSION_LABELS
    }
    evidence_cases = set().union(
        cases_by_dimension["citation_shortfall"],
        cases_by_dimension["source_not_retrieved"],
        cases_by_dimension["evidence_provenance"],
        cases_by_dimension["invalid_citation"],
    )
    citation_cases = cases_by_dimension["citation_shortfall"]
    source_link_cases = set().union(
        cases_by_dimension["source_not_retrieved"],
        cases_by_dimension["evidence_provenance"],
        cases_by_dimension["invalid_citation"],
    )
    workflow_cases = cases_by_dimension["workflow_incomplete"]
    failure_count = len(failures)

    def recommendation(
        priority: int,
        change_id: str,
        title: str,
        case_ids: set[str],
        target_files: list[str],
        implementation: list[str],
        validation: list[str],
    ) -> dict[str, Any]:
        return {
            "priority": priority,
            "change_id": change_id,
            "title": title,
            "potentially_addressed_cases": sorted(case_ids),
            "potential_coverage_count": len(case_ids),
            "potential_coverage_rate": round(
                len(case_ids) / failure_count if failure_count else 0,
                4,
            ),
            "coverage_is_not_a_predicted_pass_rate": True,
            "target_files": target_files,
            "implementation": implementation,
            "validation": validation,
        }

    return [
        recommendation(
            1,
            "evidence_inventory_gate",
            "Add a structured evidence inventory and block drafting until it is valid",
            evidence_cases,
            [
                "src/workflow/deepagents_runner.py",
                "src/workflow/delegation_guard.py",
                "src/tools/lib/prompts.py",
                "src/workflow/evidence_inventory.py (new)",
            ],
            [
                "Record canonical URLs returned by web_search and successful web_fetch calls in a structured per-run evidence inventory.",
                "Before analyst delegation or draft creation, verify that the inventory contains at least the case-specific minimum number of distinct source pages.",
                "Allow the final report to cite only inventory entries that are also present in findings or analysis.",
                "Return an actionable deficit to the agent while recovery budget remains instead of discovering the violation after the run.",
            ],
            [
                "Unit-test URL canonicalization, duplicate pages, provenance checks, and citation deficits.",
                "Run the frozen failure cases as a v2 regression set; do not replace v1 results.",
            ],
        ),
        recommendation(
            2,
            "citation_aware_budget_allocation",
            "Reserve research capacity for citation recovery and assign distinct source targets",
            citation_cases,
            [
                "src/workflow/deepagents_runner.py",
                "src/tools/lib/prompts.py",
            ],
            [
                "Require the research plan to allocate enough distinct source-page targets to satisfy the citation threshold before delegation starts.",
                "Reserve one bounded recovery opportunity until the evidence inventory passes, instead of exhausting all search and researcher calls during initial exploration.",
                "Make each researcher report the exact distinct URLs it preserved so the orchestrator can choose a non-duplicate recovery target.",
            ],
            [
                "Assert that a five-citation case cannot enter drafting with fewer than five eligible evidence URLs.",
                "Measure completion, search calls, latency, and token usage on the citation-shortfall regression subset.",
            ],
        ),
        recommendation(
            3,
            "citation_allowlist_and_url_normalization",
            "Generate final citations from an allowlist of canonical evidence URLs",
            source_link_cases,
            [
                "src/workflow/evidence_inventory.py (new)",
                "src/tools/lib/prompts.py",
                "evals/scoring.py",
            ],
            [
                "Normalize harmless URL variants consistently while preserving the exact fetched or searched URL for audit evidence.",
                "Expose the eligible citation allowlist to the editor and finalization stage.",
                "Reject invented paths, altered documentation URLs, and citations introduced only during drafting or editing.",
            ],
            [
                "Add regression fixtures for path-versus-dot URL variants, fragments, redirects, and query strings.",
                "Verify zero citations_not_retrieved and zero citations_without_evidence on the affected cases.",
            ],
        ),
        recommendation(
            4,
            "phase_state_machine_finalizer",
            "Enforce draft, editor, and final-report completion with explicit phase state",
            workflow_cases,
            [
                "src/workflow/deepagents_runner.py",
                "src/workflow/delegation_guard.py",
            ],
            [
                "Track workflow phases explicitly rather than relying only on prompt instructions.",
                "If research and analysis are complete but the agent attempts to stop, resume only the missing draft, review, or finalization phase within the existing limits.",
                "Persist the terminal phase and reason in run metadata for auditability.",
            ],
            [
                "Simulate an agent stopping after analysis and assert that finalization resumes once without looping.",
                "Keep the existing timeout, editor, and draft-edit limits enforced.",
            ],
        ),
    ]


def build_failure_analysis(
    runs: list[dict[str, Any]],
    *,
    source_bundle: str,
    generated_at: str,
) -> dict[str, Any]:
    failures: list[dict[str, Any]] = []
    for run in runs:
        if run.get("status") == "completed":
            continue
        score = run.get("score") or {}
        dimensions = classify_failure(run)
        failures.append(
            {
                "case_id": run.get("case_id"),
                "category": run.get("category"),
                "language": run.get("language"),
                "failure_type": run.get("failure_type"),
                "failure_dimensions": dimensions,
                "citation_count": score.get("citation_count"),
                "minimum_citations": score.get("minimum_citations"),
                "citation_deficit": max(
                    0,
                    int(score.get("minimum_citations") or 0)
                    - int(score.get("citation_count") or 0),
                ),
                "missing_artifacts": score.get("missing_artifacts") or [],
                "citations_not_retrieved": score.get("citations_not_retrieved") or [],
                "citations_without_evidence": score.get("citations_without_evidence") or [],
            }
        )

    dimension_counts = Counter(
        dimension
        for failure in failures
        for dimension in failure["failure_dimensions"]
    )
    dimensions = [
        {
            "dimension": dimension,
            "label": DIMENSION_LABELS[dimension],
            "case_count": count,
            "case_ids": sorted(
                failure["case_id"]
                for failure in failures
                if dimension in failure["failure_dimensions"]
            ),
        }
        for dimension, count in sorted(
            dimension_counts.items(), key=lambda item: (-item[1], item[0])
        )
    ]

    completed_count = sum(run.get("status") == "completed" for run in runs)
    return {
        "schema_version": 1,
        "generated_at": generated_at,
        "source_bundle": source_bundle,
        "run_count": len(runs),
        "completed_count": completed_count,
        "failed_count": len(failures),
        "completion_rate": round(completed_count / len(runs) if runs else 0, 4),
        "failure_dimensions_overlap": True,
        "dimension_counts": dimensions,
        "by_category": _group_summary(runs, "category"),
        "by_language": _group_summary(runs, "language"),
        "failed_cases": failures,
        "change_priorities": _change_priorities(failures),
        "interpretation_guardrail": (
            "Potential coverage counts identify observed failure conditions targeted by a "
            "change. They are not predicted pass counts and require a new versioned evaluation."
        ),
    }


def _write_markdown(path: Path, analysis: dict[str, Any]) -> None:
    dimension_rows = [
        f"| {item['dimension']} | {item['case_count']} | "
        f"{', '.join(item['case_ids'])} |"
        for item in analysis["dimension_counts"]
    ]
    category_rows = [
        f"| {item['category']} | {item['completed_count']}/{item['run_count']} | "
        f"{item['completion_rate']:.2%} |"
        for item in analysis["by_category"]
    ]
    language_rows = [
        f"| {item['language']} | {item['completed_count']}/{item['run_count']} | "
        f"{item['completion_rate']:.2%} |"
        for item in analysis["by_language"]
    ]
    recommendation_sections: list[str] = []
    for item in analysis["change_priorities"]:
        recommendation_sections.extend(
            [
                f"### P{item['priority']}: {item['title']}",
                "",
                (
                    f"- Potential coverage: {item['potential_coverage_count']}/"
                    f"{analysis['failed_count']} observed failures "
                    f"({item['potential_coverage_rate']:.2%})"
                ),
                f"- Cases: {', '.join(item['potentially_addressed_cases']) or 'none'}",
                f"- Target files: {', '.join(f'`{name}`' for name in item['target_files'])}",
                "- Implementation:",
                *[f"  - {line}" for line in item["implementation"]],
                "- Validation:",
                *[f"  - {line}" for line in item["validation"]],
                "",
            ]
        )

    report = "\n".join(
        [
            "# Deep Research Main Benchmark Failure Analysis",
            "",
            f"- Source bundle: `{analysis['source_bundle']}`",
            f"- Runs: {analysis['run_count']}",
            f"- Completed: {analysis['completed_count']}",
            f"- Failed: {analysis['failed_count']}",
            f"- Completion rate: {analysis['completion_rate']:.2%}",
            "",
            "## Failure Dimensions",
            "",
            "Failure dimensions overlap; counts must not be summed as unique failures.",
            "",
            "| Dimension | Cases | Case IDs |",
            "| --- | ---: | --- |",
            *dimension_rows,
            "",
            "## Completion by Category",
            "",
            "| Category | Completed | Rate |",
            "| --- | ---: | ---: |",
            *category_rows,
            "",
            "## Completion by Language",
            "",
            "| Language | Completed | Rate |",
            "| --- | ---: | ---: |",
            *language_rows,
            "",
            "## Prioritized Code Changes",
            "",
            *recommendation_sections,
            "## Interpretation Guardrail",
            "",
            analysis["interpretation_guardrail"],
            "",
        ]
    )
    path.write_text(report, encoding="utf-8")


def analyze_published_failures(
    published_dir: Path,
    *,
    generated_at: str | None = None,
) -> dict[str, Any]:
    runs_path = published_dir / "rescored_runs.jsonl"
    manifest_path = published_dir / "manifest.json"
    if not runs_path.is_file():
        raise FileNotFoundError(f"missing published runs: {runs_path}")
    if not manifest_path.is_file():
        raise FileNotFoundError(f"missing published manifest: {manifest_path}")

    analysis = build_failure_analysis(
        _read_jsonl(runs_path),
        source_bundle=published_dir.name,
        generated_at=generated_at or datetime.now(UTC).isoformat(),
    )
    json_path = published_dir / "failure_analysis.json"
    markdown_path = published_dir / "failure_analysis.md"
    _write_json(json_path, analysis)
    _write_markdown(markdown_path, analysis)

    manifest = _read_json(manifest_path)
    manifest["failure_analysis"] = {
        "generated_at": analysis["generated_at"],
        "json_sha256": _sha256(json_path),
        "markdown_sha256": _sha256(markdown_path),
    }
    _write_json(manifest_path, manifest)
    return analysis


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Classify published evaluation failures and rank code changes"
    )
    parser.add_argument(
        "--published-dir",
        default="evals/results/published/main_v1",
    )
    args = parser.parse_args()
    analysis = analyze_published_failures(
        (PROJECT_ROOT / args.published_dir).resolve()
    )
    print(json.dumps(analysis, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
