from pathlib import Path
import asyncio

from src.workflow.deepagents_runner import (
    SearchBudget,
    build_deepagents_system_prompt,
    build_deepagents_subagents,
    create_limited_web_search,
)
from src.tools.calculator import structured_calculator


def test_deep_research_skill_exists():
    path = Path("skills/deep-research/SKILL.md")
    text = path.read_text(encoding="utf-8")

    assert path.exists()
    assert "name: deep-research" in text
    assert "description:" in text
    assert "Research Workflow" in text


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
    assert "task_analyst" in prompt or "禁止调用" in prompt


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

