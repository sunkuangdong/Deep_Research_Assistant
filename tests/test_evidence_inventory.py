from __future__ import annotations

import asyncio
import json
from pathlib import Path
from types import SimpleNamespace

from langchain_core.messages import ToolMessage

from src.workflow.deepagents_runner import DelegationBudget, SearchBudget
from src.workflow.delegation_guard import DelegationLimitMiddleware
from src.workflow.evidence_inventory import (
    EvidenceInventory,
    create_evidence_inventory_tool,
    extract_http_urls,
)


def _write_findings(workspace: Path, name: str, text: str) -> None:
    sources = workspace / "sources"
    sources.mkdir(parents=True, exist_ok=True)
    (sources / name).write_text(text, encoding="utf-8")


def _write_research_plan(workspace: Path, lines: list[str]) -> None:
    sources = workspace / "sources"
    sources.mkdir(parents=True, exist_ok=True)
    (sources / "research_plan.md").write_text(
        "# Research Plan\n\n## Evidence Targets\n" + "\n".join(lines),
        encoding="utf-8",
    )


def _request(name: str, args: dict, call_id: str = "call-1") -> SimpleNamespace:
    return SimpleNamespace(tool_call={"name": name, "args": args, "id": call_id})


def test_inventory_normalizes_duplicates_and_requires_provenance(tmp_path: Path):
    workspace = tmp_path / "workspace"
    retrieved = {
        "https://Docs.Example/guide/#intro",
        "https://docs.example/guide",
        "https://other.example/source/",
    }
    _write_findings(
        workspace,
        "findings_one.md",
        "- [Guide](https://docs.example/guide)\n"
        "- [Invented](https://invented.example/page)\n",
    )
    inventory = EvidenceInventory(
        workspace=workspace,
        retrieved_source_urls=retrieved,
        minimum_citations=2,
    )

    first = inventory.snapshot()

    assert first.retrieved_pages == [
        "https://docs.example/guide",
        "https://other.example/source",
    ]
    assert first.eligible_pages == ["https://docs.example/guide"]
    assert first.preserved_but_not_retrieved == ["https://invented.example/page"]
    assert first.citation_deficit == 1
    assert first.passed is False

    _write_findings(
        workspace,
        "findings_two.md",
        "Source: https://other.example/source\n",
    )
    second = inventory.snapshot()

    assert second.eligible_count == 2
    assert second.citation_deficit == 0
    assert second.passed is True


def test_report_gate_enforces_minimum_and_eligible_allowlist(tmp_path: Path):
    workspace = tmp_path / "workspace"
    retrieved = {
        "https://one.example/source",
        "https://two.example/source",
    }
    _write_findings(
        workspace,
        "findings_sources.md",
        "https://one.example/source\nhttps://two.example/source\n",
    )
    inventory = EvidenceInventory(
        workspace=workspace,
        retrieved_source_urls=retrieved,
        minimum_citations=2,
    )

    too_few = inventory.evaluate_gate(
        "final_report",
        output_text="Only https://one.example/source",
        enforce_output_citations=True,
    )
    invented = inventory.evaluate_gate(
        "final_report",
        output_text=(
            "https://one.example/source https://two.example/source "
            "https://invented.example/source"
        ),
        enforce_output_citations=True,
    )
    valid = inventory.evaluate_gate(
        "final_report",
        output_text=("https://one.example/source https://two.example/source#details"),
        enforce_output_citations=True,
    )

    assert too_few.passed is False
    assert too_few.output_citation_deficit == 1
    assert invented.passed is False
    assert invented.ineligible_output_citations == ("https://invented.example/source",)
    assert valid.passed is True


def test_middleware_blocks_analyst_without_spending_delegation_budget(
    tmp_path: Path,
):
    workspace = tmp_path / "workspace"
    inventory = EvidenceInventory(
        workspace=workspace,
        retrieved_source_urls={"https://docs.example/source"},
        minimum_citations=1,
    )
    budget = DelegationBudget(max_analyst=1)
    guard = DelegationLimitMiddleware(
        budget,
        evidence_inventory=inventory,
    )
    request = _request(
        "task",
        {
            "subagent_type": "analyst",
            "description": "Analyze the findings",
        },
    )

    blocked = guard.wrap_tool_call(request, lambda _request: "OK")

    assert isinstance(blocked, ToolMessage)
    assert "Evidence gate failed" in blocked.content
    assert budget.analyst_attempts == 0
    assert budget.analyst_calls == 0

    _write_findings(
        workspace,
        "findings_source.md",
        "Source: https://docs.example/source",
    )

    assert guard.wrap_tool_call(request, lambda _request: "OK") == "OK"
    assert budget.analyst_attempts == 1
    assert budget.analyst_calls == 1


def test_middleware_blocks_draft_and_invalid_final_report(tmp_path: Path):
    workspace = tmp_path / "workspace"
    inventory = EvidenceInventory(
        workspace=workspace,
        retrieved_source_urls={"https://docs.example/source"},
        minimum_citations=1,
    )
    guard = DelegationLimitMiddleware(
        DelegationBudget(),
        evidence_inventory=inventory,
    )
    handler = lambda _request: "OK"

    blocked_draft = guard.wrap_tool_call(
        _request(
            "write_file",
            {
                "file_path": "/workspace/reports/draft_topic.md",
                "content": "Draft",
            },
        ),
        handler,
    )
    assert isinstance(blocked_draft, ToolMessage)

    _write_findings(
        workspace,
        "findings_source.md",
        "Source: https://docs.example/source",
    )
    assert (
        guard.wrap_tool_call(
            _request(
                "write_file",
                {
                    "file_path": "/workspace/reports/draft_topic.md",
                    "content": "Draft",
                },
            ),
            handler,
        )
        == "OK"
    )

    blocked_report = guard.wrap_tool_call(
        _request(
            "write_file",
            {
                "file_path": "/workspace/reports/report_topic_2026-10-15.md",
                "content": "Source: https://invented.example/source",
            },
        ),
        handler,
    )
    assert isinstance(blocked_report, ToolMessage)
    assert "outside the eligible allowlist" in blocked_report.content

    assert (
        guard.wrap_tool_call(
            _request(
                "write_file",
                {
                    "file_path": "/workspace/reports/report_topic_2026-10-15.md",
                    "content": "Source: https://docs.example/source",
                },
            ),
            handler,
        )
        == "OK"
    )


def test_five_citation_case_cannot_draft_with_only_four_eligible_pages(
    tmp_path: Path,
):
    workspace = tmp_path / "workspace"
    urls = {f"https://docs.example/source-{index}" for index in range(1, 6)}
    _write_findings(
        workspace,
        "findings_sources.md",
        "\n".join(sorted(urls)[:4]),
    )
    inventory = EvidenceInventory(
        workspace=workspace,
        retrieved_source_urls=urls,
        minimum_citations=5,
    )
    guard = DelegationLimitMiddleware(
        DelegationBudget(),
        evidence_inventory=inventory,
    )
    request = _request(
        "write_file",
        {
            "file_path": "/workspace/reports/draft_topic.md",
            "content": "Draft",
        },
    )

    blocked = guard.wrap_tool_call(request, lambda _request: "OK")

    assert isinstance(blocked, ToolMessage)
    assert "4 are currently eligible" in blocked.content
    assert "1 are still missing" in blocked.content

    _write_findings(
        workspace,
        "findings_recovery.md",
        sorted(urls)[4],
    )

    assert guard.wrap_tool_call(request, lambda _request: "OK") == "OK"


def test_inventory_tool_returns_structured_snapshot(tmp_path: Path):
    workspace = tmp_path / "workspace"
    _write_findings(
        workspace,
        "findings_source.md",
        "Source: https://docs.example/source",
    )
    inventory = EvidenceInventory(
        workspace=workspace,
        retrieved_source_urls={"https://docs.example/source"},
        minimum_citations=1,
    )
    inventory_tool = create_evidence_inventory_tool(inventory)

    payload = json.loads(asyncio.run(inventory_tool.ainvoke({})))

    assert payload["passed"] is True
    assert payload["eligible_count"] == 1
    assert payload["eligible_citation_urls"] == ["https://docs.example/source"]
    assert inventory.inspection_calls == 1


def test_extract_http_urls_rejects_credentials():
    assert extract_http_urls(
        "https://user:secret@example.com/path https://safe.example/path"
    ) == {"https://safe.example/path"}


def test_research_plan_gate_requires_enough_distinct_targets(tmp_path: Path):
    workspace = tmp_path / "workspace"
    inventory = EvidenceInventory(
        workspace=workspace,
        retrieved_source_urls=set(),
        minimum_citations=3,
    )
    _write_research_plan(
        workspace,
        [
            (
                "- target_id: source_1 | source_target: official model docs | "
                "findings_path: /workspace/sources/findings_models.md"
            ),
            (
                "- target_id: source_2 | source_target: official model docs | "
                "findings_path: /workspace/sources/findings_tools.md"
            ),
        ],
    )

    invalid = inventory.evaluate_research_plan()

    assert invalid.passed is False
    assert invalid.snapshot.target_deficit == 1
    assert invalid.snapshot.duplicate_source_targets == ["official model docs"]

    _write_research_plan(
        workspace,
        [
            (
                "- target_id: source_1 | source_target: official model docs | "
                "findings_path: /workspace/sources/findings_models.md"
            ),
            (
                "- target_id: source_2 | source_target: official tool docs | "
                "findings_path: /workspace/sources/findings_tools.md"
            ),
            (
                "- target_id: source_3 | source_target: official message docs | "
                "findings_path: /workspace/sources/findings_tools.md"
            ),
        ],
    )

    valid = inventory.evaluate_research_plan()

    assert valid.passed is True
    assert valid.snapshot.target_count == 3
    assert valid.snapshot.findings_paths[-1].endswith("findings_tools.md")


def test_researcher_recovery_slot_requires_inventory_deficit_and_marker(
    tmp_path: Path,
):
    workspace = tmp_path / "workspace"
    _write_research_plan(
        workspace,
        [
            (
                "- target_id: source_1 | source_target: official models page | "
                "findings_path: /workspace/sources/findings_models.md"
            ),
            (
                "- target_id: source_2 | source_target: official tools page | "
                "findings_path: /workspace/sources/findings_tools.md"
            ),
        ],
    )
    inventory = EvidenceInventory(
        workspace=workspace,
        retrieved_source_urls=set(),
        minimum_citations=2,
    )
    budget = DelegationBudget(
        max_researcher=3,
        reserved_researcher_calls=1,
    )
    search_budget = SearchBudget(
        max_calls=6,
        max_fetch_calls=6,
        reserved_search_calls=1,
        reserved_fetch_calls=1,
    )
    guard = DelegationLimitMiddleware(
        budget,
        evidence_inventory=inventory,
        search_budget=search_budget,
    )
    handler = lambda _request: "OK"

    for index in range(2):
        assert (
            guard.wrap_tool_call(
                _request(
                    "task",
                    {
                        "subagent_type": "researcher",
                        "description": (
                            f"Initial research {index}; write "
                            f"/workspace/sources/findings_initial_{index}.md"
                        ),
                    },
                    call_id=f"initial-{index}",
                ),
                handler,
            )
            == "OK"
        )

    before_inventory = guard.wrap_tool_call(
        _request(
            "task",
            {
                "subagent_type": "researcher",
                "description": (
                    "[EVIDENCE_RECOVERY] write "
                    "/workspace/sources/findings_recovery.md"
                ),
            },
            call_id="recovery-before-inventory",
        ),
        handler,
    )
    assert isinstance(before_inventory, ToolMessage)
    assert "check_evidence_inventory" in before_inventory.content

    inventory.inspect()
    missing_marker = guard.wrap_tool_call(
        _request(
            "task",
            {
                "subagent_type": "researcher",
                "description": (
                    "Write /workspace/sources/findings_recovery.md"
                ),
            },
            call_id="recovery-missing-marker",
        ),
        handler,
    )
    assert isinstance(missing_marker, ToolMessage)
    assert "[EVIDENCE_RECOVERY]" in missing_marker.content

    recovery = guard.wrap_tool_call(
        _request(
            "task",
            {
                "subagent_type": "researcher",
                "description": (
                    "[EVIDENCE_RECOVERY] deficit=2; eligible=[]; target the "
                    "official message page; write "
                    "/workspace/sources/findings_recovery.md"
                ),
            },
            call_id="recovery-valid",
        ),
        handler,
    )

    assert recovery == "OK"
    assert budget.researcher_calls == 3
    assert budget.researcher_recovery_calls == 1
    assert budget.researcher_recovery_attempts == 3
    assert budget.researcher_recovery_rejections == 2
    assert search_budget.recovery_active is True


def test_researcher_recovery_is_rejected_when_inventory_already_passes(
    tmp_path: Path,
):
    workspace = tmp_path / "workspace"
    _write_research_plan(
        workspace,
        [
            (
                "- target_id: source_1 | source_target: official models page | "
                "findings_path: /workspace/sources/findings_models.md"
            ),
        ],
    )
    _write_findings(
        workspace,
        "findings_models.md",
        "## Preserved Source URLs\n- https://docs.example/models",
    )
    inventory = EvidenceInventory(
        workspace=workspace,
        retrieved_source_urls={"https://docs.example/models"},
        minimum_citations=1,
    )
    inventory.inspect()
    budget = DelegationBudget(
        max_researcher=3,
        reserved_researcher_calls=1,
    )
    budget.researcher_calls = 2
    guard = DelegationLimitMiddleware(budget, evidence_inventory=inventory)

    rejected = guard.wrap_tool_call(
        _request(
            "task",
            {
                "subagent_type": "researcher",
                "description": (
                    "[EVIDENCE_RECOVERY] write "
                    "/workspace/sources/findings_extra.md"
                ),
            },
        ),
        lambda _request: "unexpected",
    )

    assert isinstance(rejected, ToolMessage)
    assert "已经达到" in rejected.content
    assert budget.researcher_calls == 2
