from __future__ import annotations

import re
from pathlib import Path
from typing import Any

ARTIFACT_PATTERNS = {
    "question": "sources/question.txt",
    "research_plan": "sources/research_plan.md",
    "findings": "sources/findings_*.md",
    "analysis": "sources/analysis_*.md",
    "draft": "reports/draft_*.md",
    "report": "reports/report_*.md",
}
URL_RE = re.compile(r"https?://[^\s<>\])}]+", re.IGNORECASE)
HEADING_RE = re.compile(r"^#{1,6}\s+(.+?)\s*$", re.MULTILINE)


def _normalize_heading(value: str) -> str:
    return re.sub(r"[^\w\u4e00-\u9fff]+", " ", value.casefold()).strip()


def _artifact_matches(workspace: Path, name: str) -> list[Path]:
    return sorted(path for path in workspace.glob(ARTIFACT_PATTERNS[name]) if path.is_file())


def score_workspace(
    workspace: Path,
    case: dict[str, Any],
    metadata: dict[str, Any],
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
    report_text = report_paths[-1].read_text(encoding="utf-8") if report_paths else ""
    actual_headings = {_normalize_heading(value) for value in HEADING_RE.findall(report_text)}
    missing_sections = [
        section
        for section in case["required_sections"]
        if _normalize_heading(section) not in actual_headings
    ]
    citations = sorted(set(URL_RE.findall(report_text)))

    budget_checks = {
        "search": int(metadata.get("search_calls", 0))
        <= int(metadata.get("search_call_limit", 0)),
        "analyst": int(metadata.get("analyst_calls", 0))
        <= int(metadata.get("analyst_call_limit", 0)),
        "editor": int(metadata.get("editor_calls", 0))
        <= int(metadata.get("editor_call_limit", 0)),
    }
    completed = (
        not missing
        and not invalid_paths
        and not missing_sections
        and len(citations) >= case["minimum_citations"]
        and all(budget_checks.values())
    )
    return {
        "completed": completed,
        "artifact_files": artifact_files,
        "artifact_completeness": (len(required) - len(missing)) / len(required),
        "missing_artifacts": missing,
        "invalid_artifact_paths": sorted(invalid_paths),
        "missing_sections": missing_sections,
        "citation_count": len(citations),
        "minimum_citations": case["minimum_citations"],
        "budget_checks": budget_checks,
    }
