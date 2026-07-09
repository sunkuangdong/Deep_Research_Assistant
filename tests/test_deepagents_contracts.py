from pathlib import Path

from src.workflow.deepagents_runner import (
    SearchBudget,
    build_deepagents_system_prompt,
    build_deepagents_subagents,
    create_limited_web_search,
)


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
    assert subagents[1]["tools"] == []


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