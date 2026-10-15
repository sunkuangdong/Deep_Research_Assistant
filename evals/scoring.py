from __future__ import annotations

import re
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit, urlunsplit

ARTIFACT_PATTERNS = {
    "question": "sources/question.txt",
    "research_plan": "sources/research_plan.md",
    "findings": "sources/findings_*.md",
    "analysis": "sources/analysis_*.md",
    "draft": "reports/draft_*.md",
    "report": "reports/report_*.md",
}
# Markdown evidence commonly wraps bare URLs in backticks or quotes. These
# delimiters are presentation syntax and must not become part of the URL used
# for provenance comparison.
URL_RE = re.compile(r'''https?://[^\s<>\])}`'"]+''', re.IGNORECASE)
HEADING_RE = re.compile(r"^#{1,6}\s+(.+?)\s*$", re.MULTILINE)
CJK_RE = re.compile(r"[\u3400-\u4dbf\u4e00-\u9fff]")
LATIN_RE = re.compile(r"[A-Za-z]")


def _normalize_heading(value: str) -> str:
    return re.sub(r"[^\w\u4e00-\u9fff]+", " ", value.casefold()).strip()


def _artifact_matches(workspace: Path, name: str) -> list[Path]:
    return sorted(path for path in workspace.glob(ARTIFACT_PATTERNS[name]) if path.is_file())


def _normalize_source_url(value: str) -> str:
    try:
        parsed = urlsplit(value.strip())
        host = (parsed.hostname or "").lower()
        if not host:
            return value.strip()
        port = f":{parsed.port}" if parsed.port is not None else ""
        path = parsed.path.rstrip("/") or "/"
        return urlunsplit((parsed.scheme.lower(), host + port, path, parsed.query, ""))
    except ValueError:
        return value.strip()


def _valid_source_url(value: str) -> bool:
    try:
        parsed = urlsplit(value)
        _ = parsed.port
        return (
            parsed.scheme.lower() in {"http", "https"}
            and bool(parsed.hostname)
            and parsed.username is None
            and parsed.password is None
        )
    except ValueError:
        return False


def _language_metrics(text: str, expected: str) -> dict[str, Any]:
    without_urls = URL_RE.sub(" ", text)
    cjk_count = len(CJK_RE.findall(without_urls))
    latin_count = len(LATIN_RE.findall(without_urls))
    letter_count = cjk_count + latin_count
    cjk_ratio = cjk_count / letter_count if letter_count else 0.0
    if expected == "en":
        passed = latin_count >= 20 and cjk_ratio <= 0.10
    else:
        passed = cjk_count >= 10 and cjk_ratio >= 0.05
    return {
        "passed": passed,
        "cjk_count": cjk_count,
        "latin_count": latin_count,
        "cjk_ratio": round(cjk_ratio, 4),
    }


def _within_budget(metadata: dict[str, Any], calls_key: str, limit_key: str) -> bool:
    if calls_key not in metadata or limit_key not in metadata:
        return False
    return int(metadata[calls_key]) <= int(metadata[limit_key])


def score_workspace(
    workspace: Path,
    case: dict[str, Any],
    metadata: dict[str, Any],
    final_text: str | None = None,
) -> dict[str, Any]:
    required = case["required_artifacts"]
    artifact_files = {
        name: [str(path.relative_to(workspace)) for path in _artifact_matches(workspace, name)]
        for name in required
    }
    missing = [name for name, paths in artifact_files.items() if not paths]

    invalid_paths: list[str] = []
    for path in workspace.rglob("*"):
        if not path.is_file():
            continue
        relative = path.relative_to(workspace).as_posix()
        name = path.name
        if name.startswith(("findings_", "analysis_")) and not relative.startswith("sources/"):
            invalid_paths.append(relative)
        if name.startswith(("draft_", "report_")) and not relative.startswith("reports/"):
            invalid_paths.append(relative)

    report_paths = _artifact_matches(workspace, "report")
    run_date = str(metadata.get("run_date") or "").strip()
    report_date_violations = (
        [
            str(path.relative_to(workspace))
            for path in report_paths
            if not path.name.endswith(f"_{run_date}.md")
        ]
        if run_date
        else []
    )
    report_date_compliance = not report_date_violations if run_date else None
    report_text = report_paths[-1].read_text(encoding="utf-8") if report_paths else ""
    actual_headings = {_normalize_heading(value) for value in HEADING_RE.findall(report_text)}
    missing_sections = [
        section
        for section in case["required_sections"]
        if _normalize_heading(section) not in actual_headings
    ]
    raw_citations = sorted(set(URL_RE.findall(report_text)))
    citations = sorted({_normalize_source_url(url) for url in raw_citations})

    invalid_citations = sorted(
        url for url in raw_citations if not _valid_source_url(url)
    )
    evidence_paths = [
        workspace / relative
        for artifact_name in ("findings", "analysis")
        for relative in artifact_files.get(artifact_name, [])
    ]
    evidence_text = "\n".join(
        path.read_text(encoding="utf-8") for path in evidence_paths if path.is_file()
    )
    evidence_urls = {
        _normalize_source_url(url) for url in URL_RE.findall(evidence_text)
    }
    retrieval_evidence_available = "retrieved_source_urls" in metadata
    retrieved_urls = {
        _normalize_source_url(str(url))
        for url in metadata.get("retrieved_source_urls", [])
        if _valid_source_url(str(url))
    }
    citations_without_evidence = sorted(set(citations) - evidence_urls)
    citations_not_retrieved = sorted(set(citations) - retrieved_urls)
    source_link_checks = {
        "syntax": not invalid_citations,
        "evidence_provenance": not citations_without_evidence,
        "retrieved_in_run": not citations_not_retrieved,
    }

    expected_language = str(case.get("language") or "en")
    language_artifacts: dict[str, dict[str, Any]] = {}
    for paths in artifact_files.values():
        for relative in paths:
            path = workspace / relative
            language_artifacts[relative] = _language_metrics(
                path.read_text(encoding="utf-8"), expected_language
            )
    language_violations = sorted(
        relative
        for relative, details in language_artifacts.items()
        if not details["passed"]
    )
    language_optional_checks: dict[str, dict[str, Any]] = {}
    todos = metadata.get("todos")
    if isinstance(todos, list) and todos:
        todo_text = "\n".join(
            str(item.get("content") or "")
            for item in todos
            if isinstance(item, dict)
        )
        language_optional_checks["todos"] = _language_metrics(
            todo_text, expected_language
        )
    if final_text:
        language_optional_checks["final_response"] = _language_metrics(
            final_text, expected_language
        )
    language_compliance = not language_violations and all(
        details["passed"] for details in language_optional_checks.values()
    )

    budget_fields = {
        "search": ("search_calls", "search_call_limit"),
        "fetch": ("fetch_calls", "fetch_call_limit"),
        "researcher": ("researcher_calls", "researcher_call_limit"),
        "analyst": ("analyst_calls", "analyst_call_limit"),
        "editor": ("editor_calls", "editor_call_limit"),
        "draft_edit": ("draft_edit_calls", "draft_edit_call_limit"),
    }
    missing_budget_metrics = sorted(
        name
        for name, keys in budget_fields.items()
        if any(key not in metadata for key in keys)
    )
    budget_checks = {
        "search": _within_budget(
            metadata, "search_calls", "search_call_limit"
        ),
        "fetch": _within_budget(
            metadata, "fetch_calls", "fetch_call_limit"
        ),
        "researcher": _within_budget(
            metadata, "researcher_calls", "researcher_call_limit"
        ),
        "analyst": _within_budget(
            metadata, "analyst_calls", "analyst_call_limit"
        ),
        "editor": _within_budget(
            metadata, "editor_calls", "editor_call_limit"
        ),
        "draft_edit": _within_budget(
            metadata, "draft_edit_calls", "draft_edit_call_limit"
        ),
    }
    completed = (
        not missing
        and not invalid_paths
        and not missing_sections
        and len(citations) >= case["minimum_citations"]
        and all(budget_checks.values())
        and language_compliance
        and all(source_link_checks.values())
        and report_date_compliance is not False
    )
    return {
        "completed": completed,
        "artifact_files": artifact_files,
        "artifact_completeness": (len(required) - len(missing)) / len(required),
        "missing_artifacts": missing,
        "invalid_artifact_paths": sorted(invalid_paths),
        "missing_sections": missing_sections,
        "report_date_compliance": report_date_compliance,
        "report_date_violations": report_date_violations,
        "citation_count": len(citations),
        "minimum_citations": case["minimum_citations"],
        "invalid_citations": invalid_citations,
        "citations_without_evidence": citations_without_evidence,
        "citations_not_retrieved": citations_not_retrieved,
        "retrieval_evidence_available": retrieval_evidence_available,
        "source_link_checks": source_link_checks,
        "language_compliance": language_compliance,
        "language_violations": language_violations,
        "language_checks": {
            "expected": expected_language,
            "artifacts": language_artifacts,
            **language_optional_checks,
        },
        "budget_checks": budget_checks,
        "missing_budget_metrics": missing_budget_metrics,
    }
