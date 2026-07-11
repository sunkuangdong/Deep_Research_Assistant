from pathlib import Path
import asyncio

from src.tools.deepagents_adapter import _format_deepagents_event
from src.workflow.deepagents_runner import (
    SearchBudget,
    build_deepagents_system_prompt,
    build_deepagents_subagents,
    create_limited_web_search,
    reset_workspace_run_artifacts,
)
from src.tools.calculator import structured_calculator
from src.workflow.deepagents_runner import DeepAgentsRunResult

def test_web_research_skill_exists():
    path = Path("skills/web-research/SKILL.md")
    text = path.read_text(encoding="utf-8")

    assert path.exists()
    assert "name: web-research" in text
    assert "description:" in text
    assert "联网调研技能" in text


def test_report_writer_skill_exists():
    path = Path("skills/report-writer/SKILL.md")
    text = path.read_text(encoding="utf-8")

    assert path.exists()
    assert "name: report-writer" in text
    assert "description:" in text
    assert "报告撰写技能" in text


def test_agents_memory_exists():
    path = Path("AGENTS.md")
    text = path.read_text(encoding="utf-8")

    assert path.exists()
    assert "Deep Research Assistant" in text
    assert "Language Policy" in text
    assert "Research Integrity" in text


def test_deepagents_prompt_contains_orchestration_rules():
    prompt = build_deepagents_system_prompt(no_analysis=False)

    assert "DeepAgents Orchestration Rules" in prompt
    assert "researcher subagent" in prompt
    assert "analyst subagent" in prompt
    assert "editor subagent" in prompt
    assert "Analysis Requirement" in prompt


def test_deepagents_prompt_no_analysis_guard():
    prompt = build_deepagents_system_prompt(no_analysis=True)

    assert "Analysis Requirement" not in prompt
    assert "禁止委派 analyst 子 Agent" in prompt


def test_subagents_with_analysis():
    search_tool = create_limited_web_search(SearchBudget(max_calls=2))
    subagents = build_deepagents_subagents(search_tool, no_analysis=False)

    assert [x["name"] for x in subagents] == ["researcher", "analyst", "editor"]
    assert subagents[0]["tools"][0].name == "web_search"
    assert [tool.name for tool in subagents[1]["tools"]] == ["structured_calculator"]


def test_subagents_without_analysis():
    search_tool = create_limited_web_search(SearchBudget(max_calls=2))
    subagents = build_deepagents_subagents(search_tool, no_analysis=True)

    assert [x["name"] for x in subagents] == ["researcher", "editor"]


def test_limited_web_search_contract():
    search_budget = SearchBudget(max_calls=2)
    search_tool = create_limited_web_search(search_budget)

    assert search_tool.name == "web_search"
    assert search_budget.max_calls == 2
    assert search_budget.call_count == 0

def test_analyst_prompt_requires_calculator():
    from src.tools.lib.prompts import ANALYST_SYSTEM_PROMPT

    assert "structured_calculator" in ANALYST_SYSTEM_PROMPT
    assert "禁止凭直觉猜测数字" in ANALYST_SYSTEM_PROMPT
    assert "禁止手算复杂数字" in ANALYST_SYSTEM_PROMPT
    assert "/workspace/sources/analysis_" in ANALYST_SYSTEM_PROMPT

def test_structured_calculator_rank_desc():
    async def run():
        return await structured_calculator.ainvoke(
            {
                "operation": "rank_desc",
                "values": [10, 30, 20],
                "labels": ["A", "B", "C"],
            }
        )

    result = asyncio.run(run())

    assert "排名结果" in result
    assert "1. B: 30.0" in result
    assert "2. C: 20.0" in result
    assert "3. A: 10.0" in result

def test_deepagents_run_result_metadata_contract():
    result = DeepAgentsRunResult(
        final_text="ok",
        metadata={
            "runtime": "deepagents",
            "skills": ["./skills"],
            "memory": ["./AGENTS.md"],
            "workspace": "/workspace",
            "workspace_sources": "/workspace/sources",
            "workspace_reports": "/workspace/reports",
            "expected_report_glob": "/workspace/reports/report_*.md",
            "subagents": ["researcher", "analyst", "editor"],
            "no_analysis": False,
            "analysis_enabled": True,
            "run_date": "2026-07-10",
            "search_calls": 1,
            "search_call_limit": 6,
        },
    )

    assert result.final_text == "ok"
    assert result.metadata["workspace"] == "/workspace"
    assert result.metadata["expected_report_glob"] == "/workspace/reports/report_*.md"
    assert result.metadata["run_date"] == "2026-07-10"


def test_official_source_quality_guardrails():
    from src.tools.lib.prompts import ORCHESTRATOR_SYSTEM_PROMPT

    web_research = Path("skills/web-research/SKILL.md").read_text(encoding="utf-8")
    report_writer = Path("skills/report-writer/SKILL.md").read_text(encoding="utf-8")

    for text in [ORCHESTRATOR_SYSTEM_PROMPT, web_research, report_writer]:
        assert "未检索到官方原始页面" in text
        assert "第三方来源" in text
        assert "禁止" in text and "冒充" in text


def test_report_date_uses_runtime_date():
    from src.tools.lib.prompts import ORCHESTRATOR_SYSTEM_PROMPT

    report_writer = Path("skills/report-writer/SKILL.md").read_text(encoding="utf-8")

    assert "运行日期" in ORCHESTRATOR_SYSTEM_PROMPT
    assert "运行日期" in report_writer
    assert "YYYY-MM-DD" not in ORCHESTRATOR_SYSTEM_PROMPT
    assert "YYYY-MM-DD" not in report_writer


def test_orchestrator_does_not_ask_for_confirmation():
    from src.tools.lib.prompts import ORCHESTRATOR_SYSTEM_PROMPT

    assert "禁止要求用户确认数据、来源或是否继续" in ORCHESTRATOR_SYSTEM_PROMPT
    assert "不要停下来询问用户" in ORCHESTRATOR_SYSTEM_PROMPT
    assert "必须继续完成 analysis、draft、editor 审阅和 final report" in ORCHESTRATOR_SYSTEM_PROMPT
    assert "禁止跳过调研" in ORCHESTRATOR_SYSTEM_PROMPT


def test_orchestrator_anti_loop_rules():
    from src.tools.lib.prompts import ORCHESTRATOR_SYSTEM_PROMPT, RUNTIME_DELEGATION_GUARD

    assert "禁止再次 write_file / edit_file 改写 findings" in ORCHESTRATOR_SYSTEM_PROMPT
    assert "禁止调用 general-purpose" in ORCHESTRATOR_SYSTEM_PROMPT
    assert "analyst 每份报告最多调用一次" in ORCHESTRATOR_SYSTEM_PROMPT
    assert "禁止委派 general-purpose" in RUNTIME_DELEGATION_GUARD


def test_event_formatter_shows_web_search_query():
    formatted = _format_deepagents_event(
        {
            "event": "on_tool_start",
            "name": "web_search",
            "data": {"input": {"query": "2023年省级GDP", "count": 5}},
        }
    )

    assert formatted is not None
    assert "web_search" in formatted
    assert "2023年省级GDP" in formatted


def test_reset_workspace_run_artifacts_keeps_readme():
    sources = Path("workspace/sources")
    reports = Path("workspace/reports")
    sources.mkdir(parents=True, exist_ok=True)
    reports.mkdir(parents=True, exist_ok=True)

    stale_source = sources / "stale_findings.md"
    stale_report = reports / "stale_report.md"
    stale_source.write_text("stale", encoding="utf-8")
    stale_report.write_text("stale", encoding="utf-8")

    reset_workspace_run_artifacts()

    assert not stale_source.exists()
    assert not stale_report.exists()
    assert (sources / "README.md").exists() or (Path("workspace/README.md")).exists()

