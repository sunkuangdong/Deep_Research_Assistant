from __future__ import annotations
from src.tools.deepagents_adapter import (
    build_deep_agent,
    run_deep_agent_once,
    DeepAgentBuildConfig,
)
from src.tools.lib.prompts import (
    ORCHESTRATOR_SYSTEM_PROMPT,
    RUNTIME_DELEGATION_GUARD,
    RUNTIME_NO_ANALYSIS_GUARD,
    RESEARCHER_SYSTEM_PROMPT,
    ANALYST_SYSTEM_PROMPT,
    EDITOR_SYSTEM_PROMPT,
)
from langchain_core.tools import tool
from src.tools.search import WebSearchInput, bocha_web_search

DEEPAGENTS_ORCHESTRATION_GUARD = """
[DeepAgents Orchestration Rules]
You are running in official DeepAgents mode.
Available collaboration options:
- Use the main web_search tool only for quick verification or simple lookup.
- Delegate focused research tasks to the researcher subagent.
- Delegate structured comparison, trend reasoning, trade-off reasoning, and uncertainty assessment to the analyst subagent.
- Delegate draft review to the editor subagent.
Delegation policy:
- For complex research, first create a short plan.
- Use at most 3 researcher delegations.
- Each researcher delegation must cover exactly one focused subtopic.
- Do not ask one researcher to investigate multiple unrelated subtopics.
- Use analyst only after research evidence is available.
- Use editor once near the end to review the draft.
- Do not delegate unnecessary work just to use subagents.
Search budget:
- For simple lookup tasks, use at most 1 direct web_search call.
- For comparison tasks, use at most 4 total web_search calls.
- For deep research tasks, use at most 6 total web_search calls.
- The main agent should not call web_search more than 2 times directly.
- Prefer delegating focused research to the researcher subagent instead of repeatedly searching in the main agent.
- Stop searching once there is enough evidence to answer.
- Do not search separately for every small wording variation of the same concept.
Output policy:
- Final output must be in Chinese.
- Include evidence or source names when available.
- Clearly mark uncertainty and limitations.
"""

def create_limited_web_search(max_calls: int = 6) -> tool:
    """
    创建带调用预算的 web_search 工具。
    这个限制是一次 run_deepagents_workflow 调用内生效的：
        - 主 Agent 和 researcher subagent 共用同一个计数器
        - 超过 max_calls 后，不再请求真实搜索 API
    """

    call_count = 0

    @tool("web_search", args_schema=WebSearchInput)
    async def limited_web_search(query: str, count: int = 10) -> str:
        """使用 Bocha 联网搜索 API 检索互联网网页，并限制单次 DeepAgents 运行中的搜索次数。"""
        nonlocal call_count

        if call_count >= max_calls:
            return (
                f"web_search 搜索预算已用完。本次最多允许 {max_calls} 次搜索，"
                "请基于已有搜索结果停止继续搜索，并直接整理最终结论。"
            )
        
        call_count += 1
        safe_count = min(call_count, 5)

        print(f"  🔎 搜索[{call_count}/{max_calls}]: {query}（{safe_count} 条）")
        return await bocha_web_search(query, safe_count)

    return limited_web_search



def build_deepagents_system_prompt(no_analysis: bool = False) -> str:
    """
    构建 DeepAgents 主 Agent 的 system_prompt。
    注意：
        - ORCHESTRATOR_SYSTEM_PROMPT 是主 Agent 的长期角色设定
        - RUNTIME_DELEGATION_GUARD 是委派约束
        - RUNTIME_NO_ANALYSIS_GUARD 是本次运行的 no_analysis 约束
    """

    sections = [
        ORCHESTRATOR_SYSTEM_PROMPT.strip(),
        DEEPAGENTS_ORCHESTRATION_GUARD.strip(),
        RUNTIME_DELEGATION_GUARD.strip(),
    ]

    if no_analysis:
        sections.append(RUNTIME_NO_ANALYSIS_GUARD.strip())

    return "\n\n".join(sections)

def build_deepagents_subagents(search_tool) -> list[Any]:
    """
    构建 DeepAgents 官方 subagents。
    researcher:
        负责一个聚焦子主题的联网调研，可以使用 web_search。
    analyst:
        负责结构化分析，不直接联网。
    editor:
        负责审阅草稿，不直接联网。
    """

    return [
        {
            "name": "researcher",
            "description": (
                "Use this subagent for focused web research on one specific "
                "subtopic. It can search the web and return evidence with URLs."
            ),
            "system_prompt": (
                RESEARCHER_SYSTEM_PROMPT.strip()
                + "\n\n[Search Budget]\n"
                + "- You may call web_search at most 2 times for one delegated subtopic.\n"
                + "- Use focused queries, not many small wording variations.\n"
                + "- Stop searching once you have enough evidence.\n"
                + "- Return concise findings with source URLs.\n"
            ),
            "tools": [search_tool],
        },
        {
            "name": "analyst",
            "description": (
                "Use this subagent for structured comparison, trend analysis, "
                "trade-off analysis, and uncertainty assessment based on provided research text."
            ),
            "system_prompt": ANALYST_SYSTEM_PROMPT,
            "tools": [],
        },
        {
            "name": "editor",
            "description": (
                "Use this subagent to review the draft report for clarity, "
                "consistency, and completeness. It does not need to search the web."
            ),
            "system_prompt": EDITOR_SYSTEM_PROMPT,
            "tools": [],
        }
    ]

async def run_deepagents_workflow(
    topic: str,
    no_analysis: bool = False,
    enabled_skills: list[str] = [],
) -> str:
    """
    运行官方 DeepAgents 工作流。
    第 4 步只建立业务编排入口。
    第 5 步会在这里接入 deepagents_adapter。
    第 6 步职责：
        1) 接收 main.py 传来的 topic / skills / no_analysis
        2) 构建 system_prompt
        3) 构建官方 DeepAgent
        4) 执行一次 agent.ainvoke
        5) 返回最终文本
    """

    clean_topic = (topic or "").strip()

    system_prompt = build_deepagents_system_prompt(no_analysis=no_analysis)

    search_tool = create_limited_web_search(max_calls=6)

    config = DeepAgentBuildConfig(
        root_dir=".",
        skills=["./skills"],
        memory=["./AGENTS.md"],
        system_prompt=system_prompt,
        debug=False,
        name="deep_research_agent",
        tools=[search_tool],
        subagents=build_deepagents_subagents(search_tool),
    )

    agent = build_deep_agent(config)

    user_prompt = (
        f"请围绕这个主题完成调研并给出最终报告：{clean_topic}\n\n"
        "要求：所有输出使用中文。"
    )

    if enabled_skills:
        user_prompt += (
            "\n\n当前 CLI 请求启用的 skills："
            f"{', '.join(enabled_skills)}。\n"
            "注意：官方 SkillsMiddleware 会在第 7 步接入 skills/ 目录后正式生效。"
        )
    
    return await run_deep_agent_once(agent, user_prompt)


