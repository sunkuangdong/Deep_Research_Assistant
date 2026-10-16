from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

from langchain_core.tools import tool

from src.tools.search import canonical_source_url

# Keep this extraction rule aligned with the deterministic evaluator. Markdown
# delimiters are excluded so the extracted value can be compared directly.
URL_RE = re.compile(r"""https?://[^\s<>\])}`'\"]+""", re.IGNORECASE)
RESEARCH_TARGET_RE = re.compile(
    r"^\s*-\s*target_id:\s*(?P<target_id>[a-z0-9][a-z0-9_-]*)\s*"
    r"\|\s*source_target:\s*(?P<source_target>.+?)\s*"
    r"\|\s*findings_path:\s*(?P<findings_path>\S+)\s*$",
    re.IGNORECASE,
)
FINDINGS_PATH_RE = re.compile(
    r"^(?:/)?workspace/sources/findings_[a-z0-9][a-z0-9_-]*\.md$"
)


def _valid_http_url(value: str) -> bool:
    try:
        parsed = urlsplit(value.strip())
        _ = parsed.port
        return (
            parsed.scheme.casefold() in {"http", "https"}
            and bool(parsed.hostname)
            and parsed.username is None
            and parsed.password is None
        )
    except ValueError:
        return False


def extract_http_urls(text: str) -> set[str]:
    """Extract syntactically valid HTTP(S) URLs from an artifact."""

    return {value for value in URL_RE.findall(text) if _valid_http_url(value)}


@dataclass(frozen=True)
class EvidenceSnapshot:
    minimum_citations: int
    retrieved_pages: list[str]
    evidence_pages: list[str]
    eligible_pages: list[str]
    eligible_citation_urls: list[str]
    evidence_files: list[str]
    evidence_file_urls: dict[str, list[str]]
    retrieved_but_not_preserved: list[str]
    preserved_but_not_retrieved: list[str]
    eligible_count: int
    citation_deficit: int
    passed: bool

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class EvidenceGateResult:
    stage: str
    passed: bool
    message: str
    snapshot: EvidenceSnapshot
    output_citation_count: int | None = None
    output_citation_deficit: int | None = None
    ineligible_output_citations: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["snapshot"] = self.snapshot.to_dict()
        return payload


@dataclass(frozen=True)
class ResearchPlanSnapshot:
    required_target_count: int
    target_count: int
    target_ids: list[str]
    source_targets: list[str]
    findings_paths: list[str]
    duplicate_target_ids: list[str]
    duplicate_source_targets: list[str]
    invalid_target_lines: list[str]
    target_deficit: int
    passed: bool

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ResearchPlanGateResult:
    passed: bool
    message: str
    snapshot: ResearchPlanSnapshot

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["snapshot"] = self.snapshot.to_dict()
        return payload


class EvidenceInventory:
    """Build and enforce a per-run allowlist of traceable evidence URLs.

    A source page becomes eligible only when both conditions hold:

    1. The current run returned it from ``web_search`` or successfully fetched it.
    2. A researcher preserved it in a findings artifact (or an analyst reused it
       in an analysis artifact).

    The inventory is computed from current runtime state on every check, so it
    cannot accidentally reuse evidence from a previous run.
    """

    def __init__(
        self,
        *,
        workspace: Path,
        retrieved_source_urls: set[str],
        minimum_citations: int,
        output_language: str = "en",
    ) -> None:
        if minimum_citations <= 0:
            raise ValueError("minimum_citations must be positive")
        if output_language not in {"en", "zh"}:
            raise ValueError("output_language must be 'en' or 'zh'")

        self.workspace = Path(workspace)
        self.retrieved_source_urls = retrieved_source_urls
        self.minimum_citations = minimum_citations
        self.output_language = output_language
        self.inspection_calls = 0
        self.gate_checks = 0
        self.gate_rejections = 0
        self.gate_events: list[dict[str, Any]] = []
        self.research_plan_checks = 0
        self.research_plan_rejections = 0
        self.research_plan_events: list[dict[str, Any]] = []

    def _evidence_paths(self) -> list[Path]:
        sources = self.workspace / "sources"
        return sorted(
            {
                *sources.glob("findings_*.md"),
                *sources.glob("analysis_*.md"),
            }
        )

    def snapshot(self) -> EvidenceSnapshot:
        retrieved_by_page = {
            canonical_source_url(raw): raw
            for raw in set(self.retrieved_source_urls)
            if _valid_http_url(raw)
        }
        evidence_by_page: dict[str, set[str]] = {}
        evidence_paths = [path for path in self._evidence_paths() if path.is_file()]
        evidence_file_urls: dict[str, list[str]] = {}
        for path in evidence_paths:
            relative_path = path.relative_to(self.workspace).as_posix()
            artifact_urls = extract_http_urls(path.read_text(encoding="utf-8"))
            evidence_file_urls[relative_path] = sorted(artifact_urls)
            for raw in artifact_urls:
                evidence_by_page.setdefault(canonical_source_url(raw), set()).add(raw)

        retrieved_pages = set(retrieved_by_page)
        evidence_pages = set(evidence_by_page)
        eligible_pages = retrieved_pages & evidence_pages
        eligible_citation_urls = [
            min(evidence_by_page[page]) for page in sorted(eligible_pages)
        ]
        eligible_count = len(eligible_pages)
        deficit = max(0, self.minimum_citations - eligible_count)

        return EvidenceSnapshot(
            minimum_citations=self.minimum_citations,
            retrieved_pages=sorted(retrieved_pages),
            evidence_pages=sorted(evidence_pages),
            eligible_pages=sorted(eligible_pages),
            eligible_citation_urls=eligible_citation_urls,
            evidence_files=[
                path.relative_to(self.workspace).as_posix() for path in evidence_paths
            ],
            evidence_file_urls=evidence_file_urls,
            retrieved_but_not_preserved=sorted(retrieved_pages - evidence_pages),
            preserved_but_not_retrieved=sorted(evidence_pages - retrieved_pages),
            eligible_count=eligible_count,
            citation_deficit=deficit,
            passed=deficit == 0,
        )

    @staticmethod
    def _normalized_source_target(value: str) -> str:
        cleaned = re.sub(r"\s+", " ", value.strip())
        if _valid_http_url(cleaned):
            return canonical_source_url(cleaned)
        return cleaned.casefold()

    @staticmethod
    def _duplicates(values: list[str]) -> list[str]:
        seen: set[str] = set()
        duplicates: set[str] = set()
        for value in values:
            if value in seen:
                duplicates.add(value)
            seen.add(value)
        return sorted(duplicates)

    def research_plan_snapshot(self) -> ResearchPlanSnapshot:
        """Validate machine-readable, distinct evidence targets in the run plan."""

        plan_path = self.workspace / "sources" / "research_plan.md"
        text = plan_path.read_text(encoding="utf-8") if plan_path.is_file() else ""
        target_ids: list[str] = []
        source_targets: list[str] = []
        findings_paths: list[str] = []
        invalid_lines: list[str] = []

        for line in text.splitlines():
            if "target_id:" not in line.casefold():
                continue
            match = RESEARCH_TARGET_RE.match(line)
            if match is None:
                invalid_lines.append(line.strip())
                continue
            target_ids.append(match.group("target_id").casefold())
            source_targets.append(
                self._normalized_source_target(match.group("source_target"))
            )
            findings_path = match.group("findings_path").replace("\\", "/")
            findings_paths.append(findings_path)
            if not FINDINGS_PATH_RE.match(findings_path):
                invalid_lines.append(line.strip())

        duplicate_ids = self._duplicates(target_ids)
        duplicate_targets = self._duplicates(source_targets)
        target_count = len(source_targets)
        deficit = max(0, self.minimum_citations - target_count)
        passed = (
            deficit == 0
            and not duplicate_ids
            and not duplicate_targets
            and not invalid_lines
        )
        return ResearchPlanSnapshot(
            required_target_count=self.minimum_citations,
            target_count=target_count,
            target_ids=target_ids,
            source_targets=source_targets,
            findings_paths=findings_paths,
            duplicate_target_ids=duplicate_ids,
            duplicate_source_targets=duplicate_targets,
            invalid_target_lines=invalid_lines,
            target_deficit=deficit,
            passed=passed,
        )

    def evaluate_research_plan(self) -> ResearchPlanGateResult:
        snapshot = self.research_plan_snapshot()
        if snapshot.passed:
            message = "Research plan evidence-target gate passed."
        elif self.output_language == "zh":
            message = (
                "调研计划门控未通过。必须在 research_plan.md 中为至少 "
                f"{snapshot.required_target_count} 个不同来源页面各写一行：\n"
                "- target_id: source_1 | source_target: <唯一的官方页面或精确页面目标> "
                "| findings_path: /workspace/sources/findings_<slug>.md\n"
                f"当前有效目标 {snapshot.target_count} 个，仍缺 "
                f"{snapshot.target_deficit} 个；重复 target_id："
                f"{snapshot.duplicate_target_ids or '无'}；重复 source_target："
                f"{snapshot.duplicate_source_targets or '无'}；格式错误行："
                f"{snapshot.invalid_target_lines or '无'}。请先一次性修正计划再委派 researcher。"
            )
        else:
            message = (
                "Research plan evidence-target gate failed. research_plan.md must "
                f"allocate at least {snapshot.required_target_count} distinct source "
                "pages using one line per target:\n"
                "- target_id: source_1 | source_target: <unique official page or "
                "precise page objective> | findings_path: "
                "/workspace/sources/findings_<slug>.md\n"
                f"Valid targets: {snapshot.target_count}; deficit: "
                f"{snapshot.target_deficit}; duplicate target IDs: "
                f"{snapshot.duplicate_target_ids or 'none'}; duplicate source targets: "
                f"{snapshot.duplicate_source_targets or 'none'}; invalid lines: "
                f"{snapshot.invalid_target_lines or 'none'}. Fix the plan before "
                "delegating a researcher."
            )

        result = ResearchPlanGateResult(
            passed=snapshot.passed,
            message=message,
            snapshot=snapshot,
        )
        self.research_plan_checks += 1
        if not snapshot.passed:
            self.research_plan_rejections += 1
        self.research_plan_events.append(
            {
                "passed": snapshot.passed,
                "target_count": snapshot.target_count,
                "target_deficit": snapshot.target_deficit,
                "duplicate_target_ids": snapshot.duplicate_target_ids,
                "duplicate_source_targets": snapshot.duplicate_source_targets,
                "invalid_target_lines": snapshot.invalid_target_lines,
            }
        )
        return result

    def _message(
        self,
        *,
        stage: str,
        snapshot: EvidenceSnapshot,
        output_citation_count: int | None,
        output_citation_deficit: int | None,
        ineligible_output_citations: list[str],
    ) -> str:
        eligible = ", ".join(snapshot.eligible_citation_urls) or "(none)"
        missing = ", ".join(snapshot.retrieved_but_not_preserved[:5]) or "(none)"
        ineligible = ", ".join(ineligible_output_citations) or "(none)"
        if self.output_language == "zh":
            return (
                f"证据门控未通过（阶段：{stage}）。要求至少 "
                f"{snapshot.minimum_citations} 个合格来源，当前有 "
                f"{snapshot.eligible_count} 个，仍缺 {snapshot.citation_deficit} 个。"
                "合格来源必须同时满足：由本轮 web_search/web_fetch 返回，且已保存在 "
                "findings/analysis 文件中。"
                f"当前合格引用：{eligible}。"
                f"已检索但尚未写入证据文件的页面：{missing}。"
                + (
                    f"当前输出包含 {output_citation_count} 个不同引用，"
                    f"仍缺 {output_citation_deficit} 个；不在合格清单中的引用：{ineligible}。"
                    if output_citation_count is not None
                    else ""
                )
                + "请使用剩余搜索/研究员预算补充新的 findings，或仅从合格引用清单中修正输出；"
                "然后调用 check_evidence_inventory 复查。"
            )
        return (
            f"Evidence gate failed at stage '{stage}'. At least "
            f"{snapshot.minimum_citations} eligible source pages are required; "
            f"{snapshot.eligible_count} are currently eligible and "
            f"{snapshot.citation_deficit} are still missing. A source is eligible only "
            "when it was returned by this run's web_search/web_fetch and preserved in "
            "a findings/analysis artifact. "
            f"Eligible citations: {eligible}. "
            f"Retrieved but not yet preserved: {missing}. "
            + (
                f"The current output has {output_citation_count} distinct citations "
                f"and is short by {output_citation_deficit}; citations outside the "
                f"eligible allowlist: {ineligible}. "
                if output_citation_count is not None
                else ""
            )
            + "Use the remaining search/researcher budget to add a new findings file, "
            "or revise the output to cite only eligible URLs, then call "
            "check_evidence_inventory again."
        )

    def evaluate_gate(
        self,
        stage: str,
        *,
        output_text: str | None = None,
        enforce_output_citations: bool = False,
    ) -> EvidenceGateResult:
        snapshot = self.snapshot()
        output_count: int | None = None
        output_deficit: int | None = None
        ineligible: list[str] = []

        if enforce_output_citations:
            output_pages = {
                canonical_source_url(raw)
                for raw in extract_http_urls(output_text or "")
            }
            output_count = len(output_pages)
            output_deficit = max(0, self.minimum_citations - output_count)
            ineligible = sorted(output_pages - set(snapshot.eligible_pages))

        passed = snapshot.passed and (
            not enforce_output_citations or (output_deficit == 0 and not ineligible)
        )
        message = (
            "Evidence gate passed."
            if passed
            else self._message(
                stage=stage,
                snapshot=snapshot,
                output_citation_count=output_count,
                output_citation_deficit=output_deficit,
                ineligible_output_citations=ineligible,
            )
        )
        result = EvidenceGateResult(
            stage=stage,
            passed=passed,
            message=message,
            snapshot=snapshot,
            output_citation_count=output_count,
            output_citation_deficit=output_deficit,
            ineligible_output_citations=tuple(ineligible),
        )
        self.gate_checks += 1
        if not passed:
            self.gate_rejections += 1
        self.gate_events.append(
            {
                "stage": stage,
                "passed": passed,
                "eligible_count": snapshot.eligible_count,
                "citation_deficit": snapshot.citation_deficit,
                "output_citation_count": output_count,
                "output_citation_deficit": output_deficit,
                "ineligible_output_citations": ineligible,
            }
        )
        return result

    def inspect(self) -> dict[str, Any]:
        self.inspection_calls += 1
        return self.snapshot().to_dict()

    def metadata(self) -> dict[str, Any]:
        return {
            **self.snapshot().to_dict(),
            "research_plan": self.research_plan_snapshot().to_dict(),
            "inspection_calls": self.inspection_calls,
            "gate_checks": self.gate_checks,
            "gate_rejections": self.gate_rejections,
            "gate_events": list(self.gate_events),
            "research_plan_checks": self.research_plan_checks,
            "research_plan_rejections": self.research_plan_rejections,
            "research_plan_events": list(self.research_plan_events),
        }


def create_evidence_inventory_tool(inventory: EvidenceInventory) -> Any:
    """Expose the current structured inventory to the orchestrator."""

    @tool("check_evidence_inventory")
    async def check_evidence_inventory() -> str:
        """Return eligible evidence URLs, the citation target, and any deficit."""

        return json.dumps(inventory.inspect(), ensure_ascii=False, indent=2)

    return check_evidence_inventory
