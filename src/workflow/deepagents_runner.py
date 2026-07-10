from __future__ import annotations
from datetime import date
from typing import Any

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

from src.tools.calculator import structured_calculator

from dataclasses import dataclass

class SearchBudget:
    def __init__(self, max_calls: int):
        self.max_calls = max_calls
        self.call_count = 0

@dataclass(frozen=True)
class DeepAgentsRunResult:
    final_text: str
    metadata: dict

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

def create_limited_web_search(search_budget: SearchBudget) -> Any:
    """
    创建带调用预算的 web_search 工具。
    这个限制是一次 run_deepagents_workflow 调用内生效的：
        - 主 Agent 和 researcher subagent 共用同一个计数器
        - 超过 max_calls 后，不再请求真实搜索 API
    """

    @tool("web_search", args_schema=WebSearchInput)
    async def limited_web_search(query: str, count: int = 10) -> str:
        """使用 Bocha 联网搜索 API 检索互联网网页，并限制单次 DeepAgents 运行中的搜索次数。"""

        if search_budget.call_count >= search_budget.max_calls:
            return (
                f"web_search 搜索预算已用完。本次最多允许 {search_budget.max_calls} 次搜索，"
                "请基于已有搜索结果停止继续搜索，并直接整理最终结论。"
            )
        search_budget.call_count += 1
        safe_count = min(count, 5)

        print(
            f"  🔎 搜索[{search_budget.call_count}/{search_budget.max_calls}]: "
            f"{query}（{safe_count} 条）"
        )
        
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
    else:
        sections.append(
            """
            [Analysis Requirement]
                - For comparison, trend, trade-off, or framework evaluation tasks, you must delegate to the analyst subagent after collecting research evidence.
                - The final answer must include an explicit analysis section.
                - The analysis must compare dimensions, trade-offs, suitable scenarios, and uncertainty.
                - Do not ask the user whether to continue analysis.
                - If the user asks for a conclusion, produce the final analysis and conclusion directly.
                - Do not stop after listing raw research findings.
                - After research is collected, synthesize the final answer without asking follow-up permission.
            """.strip()
        )

    return "\n\n".join(sections)

def build_deepagents_subagents(search_tool, no_analysis: bool = False) -> list[Any]:
    """
    构建 DeepAgents 官方 subagents。
    researcher:
        负责一个聚焦子主题的联网调研，可以使用 web_search。
    analyst:
        负责结构化分析，不直接联网。
    editor:
        负责审阅草稿，不直接联网。
    """
    subagents = [
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
        }
    ]

    if not no_analysis:
        subagents.append(
            {
                "name": "analyst",
                "description": (
                    "Use this subagent after research evidence is collected. "
                    "It must compare findings, identify trade-offs, separate facts "
                    "from assumptions, and assess uncertainty."
                ),
                "system_prompt": ANALYST_SYSTEM_PROMPT,
                "tools": [structured_calculator],
            }
        )
    subagents.append(
        {
            "name": "editor",
            "description": (
                "Use this subagent to review the draft report for clarity, "
                "consistency, evidence quality, and completeness."
            ),
            "system_prompt": EDITOR_SYSTEM_PROMPT,
            "tools": [],
        }
    )

    return subagents

async def run_deepagents_workflow(
    topic: str,
    no_analysis: bool = False,
) -> DeepAgentsRunResult:
    """
    运行官方 DeepAgents 工作流。
    建立业务编排入口。
    在这里接入 deepagents_adapter。
    职责：
        1) 接收 main.py 传来的 topic / skills / no_analysis
        2) 构建 system_prompt
        3) 构建官方 DeepAgent
        4) 执行一次 agent.ainvoke
        5) 返回最终文本
    """

    clean_topic = (topic or "").strip()

    system_prompt = build_deepagents_system_prompt(no_analysis=no_analysis)
    run_date = date.today().isoformat()
    search_budget = SearchBudget(max_calls=6)
    search_tool = create_limited_web_search(search_budget)

    subagents = build_deepagents_subagents(
        search_tool,
        no_analysis=no_analysis,
    )

    config = DeepAgentBuildConfig(
        root_dir=".",
        skills=["./skills"],
        memory=["./AGENTS.md"],
        system_prompt=system_prompt,
        debug=False,
        name="deep_research_agent",
        tools=[search_tool],
        subagents=subagents,
    )

    agent = build_deep_agent(config)

    user_prompt = (
        f"请围绕这个主题完成调研并给出最终报告：{clean_topic}\n\n"
        f"运行日期：{run_date}。报告文件名中的日期必须使用这个运行日期，禁止自行编造日期。\n"
        "要求：所有输出使用中文。\n"
        "用户已授权你完成完整调研流程，不要询问是否继续，也不要要求用户确认数据或来源；"
        "如果官方来源不足，必须标注不确定性并继续完成 final report；"
        "必须完成 question、research_plan、findings、analysis（如涉及数值）、draft、editor 审阅和 final report。"
    )
    
    final_text = await run_deep_agent_once(agent, user_prompt)

    return DeepAgentsRunResult(
        final_text=final_text,
        metadata={
            "runtime": "deepagents",
            "skills": ["./skills"],
            "memory": ["./AGENTS.md"],
            "subagents": [x["name"] for x in subagents],
            "no_analysis": no_analysis,
            "analysis_enabled": not no_analysis,
            "run_date": run_date,
            "search_calls": search_budget.call_count,
            "search_call_limit": search_budget.max_calls,
            "workspace": "/workspace",
            "workspace_sources": "/workspace/sources",
            "workspace_reports": "/workspace/reports",
            "expected_report_glob": "/workspace/reports/report_*.md",
        },
    )


