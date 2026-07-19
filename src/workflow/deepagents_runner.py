from __future__ import annotations
from datetime import date
from pathlib import Path
from typing import Any

from src.tools.deepagents_adapter import (
    build_deep_agent,
    run_deep_agent_once,
    DeepAgentBuildConfig,
    DEFAULT_TODOS_EXPORT_PATH,
)
from src.workflow.delegation_guard import DelegationLimitMiddleware

from src.tools.lib.prompts import (
    ORCHESTRATOR_SYSTEM_PROMPT,
    DEEPAGENTS_ORCHESTRATION_GUARD,
    RUNTIME_DELEGATION_GUARD,
    RUNTIME_NO_ANALYSIS_GUARD,
    RUNTIME_ANALYSIS_REQUIREMENT,
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
    
class DelegationBudget:
    def __init__(self, max_analyst: int = 1, max_editor: int = 1):
        self.max_analyst = max_analyst
        self.max_editor = max_editor
        self.analyst_calls = 0
        self.editor_calls = 0

def reset_workspace_run_artifacts() -> None:
    """
    清理上一次运行留下的过程文件，避免 Agent 误用旧 findings / 旧计划。
    保留 README.md 与 .gitkeep。
    """
    keep_names = {".gitkeep", "README.md"}

    for folder in (Path("workspace/sources"), Path("workspace/reports")):
        if not folder.exists():
            continue

        for file_path in folder.iterdir():
            if not file_path.is_file() or file_path.name in keep_names:
                continue
            file_path.unlink()

    if DEFAULT_TODOS_EXPORT_PATH.exists():
        DEFAULT_TODOS_EXPORT_PATH.unlink()

@dataclass(frozen=True)
class DeepAgentsRunResult:
    final_text: str
    metadata: dict

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
        - DEEPAGENTS_ORCHESTRATION_GUARD 是 DeepAgents 编排规则
        - RUNTIME_DELEGATION_GUARD 是委派约束
        - RUNTIME_NO_ANALYSIS_GUARD / RUNTIME_ANALYSIS_REQUIREMENT 是本次运行的分析约束
    """

    sections = [
        ORCHESTRATOR_SYSTEM_PROMPT.strip(),
        DEEPAGENTS_ORCHESTRATION_GUARD.strip(),
        RUNTIME_DELEGATION_GUARD.strip(),
    ]

    if no_analysis:
        sections.append(RUNTIME_NO_ANALYSIS_GUARD.strip())
    else:
        sections.append(RUNTIME_ANALYSIS_REQUIREMENT.strip())

    return "\n\n".join(sections)

def build_deepagents_subagents(search_tool, no_analysis: bool = False, path_guard = None) -> list[Any]:
    """
    构建 DeepAgents 官方 subagents。
    researcher:
        负责一个聚焦子主题的联网调研，可以使用 web_search。
    analyst:
        负责结构化分析，不直接联网。
    editor:
        负责审阅草稿，不直接联网。
    """
    subagent_middleware = [path_guard] if path_guard is not None else []
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
            "middleware": subagent_middleware,
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
                "middleware": subagent_middleware,
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

    path_guard = DelegationLimitMiddleware(
        DelegationBudget(max_analyst=0, max_editor=0),
        block_artifact_rewrites=False,
    )

    reset_workspace_run_artifacts()
    system_prompt = build_deepagents_system_prompt(no_analysis=no_analysis)
    run_date = date.today().isoformat()
    search_budget = SearchBudget(max_calls=6)
    search_tool = create_limited_web_search(search_budget)

    subagents = build_deepagents_subagents(
        search_tool,
        no_analysis=no_analysis,
        path_guard=path_guard,
    )

    delegation_budget = DelegationBudget(max_analyst=1, max_editor=1)
    main_guard = DelegationLimitMiddleware(delegation_budget, block_artifact_rewrites=True)

    config = DeepAgentBuildConfig(
        root_dir=".",
        skills=["./skills"],
        memory=["./AGENTS.md"],
        system_prompt=system_prompt,
        debug=False,
        name="deep_research_agent",
        tools=[search_tool],
        subagents=subagents,
        middleware=[main_guard],
    )

    agent = build_deep_agent(config)

    # 粗粒度语言跟随：主题含中日韩汉字 → 中文指令；否则英文指令。
    use_chinese = any("\u4e00" <= ch <= "\u9fff" for ch in clean_topic)
    if use_chinese:
        user_prompt = (
            f"请围绕这个主题完成调研并给出最终报告：{clean_topic}\n\n"
            f"运行日期：{run_date}。报告文件名中的日期必须使用这个运行日期，禁止自行编造日期。\n"
            "【语言】用户用中文提问，因此 todo、findings、analysis、draft、report、最终回复都必须使用中文；"
            "专有名词与 URL 可保留原文。\n"
            "【文件名约定】slug 必须全小写 ASCII（[a-z0-9_]+）；"
            "findings 只能是 /workspace/sources/findings_<slug>.md；"
            "analysis 只能是 /workspace/sources/analysis_<slug>.md；"
            "draft/report 只能写在 /workspace/reports/ 下；"
            "禁止 CamelCase、*_research.md、根路径 /findings_*.md。\n"
            "委派 researcher 时必须在 task 中写明精确写入路径；"
            "委派 analyst 时必须列出真实 findings 路径与 analysis 输出路径；"
            "读取前先 ls，禁止臆造文件名。\n"
            "用户已授权你完成完整调研流程，不要询问是否继续，也不要要求用户确认数据或来源；"
            "如果官方来源不足，必须标注不确定性并继续完成 final report；"
            "workspace 已清空，禁止复用任何与本次主题无关的旧 findings / analysis / draft / report；"
            "完成 research_plan 后，必须通过 web_search 或委派 researcher 子 Agent 完成联网调研，"
            "禁止跳过调研直接进入起草；"
            "researcher 写完 findings 后禁止主 Agent 再改 findings；"
            "analyst 最多调用 1 次，写完 analysis 后禁止主 Agent 再改 analysis；"
            "editor 最多调用 1 次；editor 返回后最多修订 draft 一次，然后必须立刻写入 final report 并结束；"
            "禁止二次委派 editor，禁止在 draft 上反复 edit/read 空转；"
            "禁止委派 general-purpose；报告起草必须由主 Agent 自己完成；"
            "必须完成 question、research_plan、findings、analysis（如涉及对比/数值）、draft、editor 审阅和 final report。"
        )
    else:
        user_prompt = (
            f"Please research this topic and produce a final report: {clean_topic}\n\n"
            f"Run date: {run_date}. The date in the report filename MUST use this run date; do not invent dates.\n"
            "[Language] The user asked in English, so todos, findings, analysis, draft, report, "
            "and the final reply MUST be in English. Keep proper nouns and URLs in original form when appropriate.\n"
            "[Filename rules] slug must be lowercase ASCII ([a-z0-9_]+); "
            "findings only under /workspace/sources/findings_<slug>.md; "
            "analysis only under /workspace/sources/analysis_<slug>.md; "
            "draft/report only under /workspace/reports/; "
            "no CamelCase, no *_research.md, no root paths like /findings_*.md.\n"
            "When delegating researcher, include the exact write path in the task; "
            "when delegating analyst, list real findings paths and the analysis output path; "
            "ls before reading; never invent filenames.\n"
            "The user has authorized a full research run: do not ask whether to continue, "
            "and do not ask the user to confirm data or sources; "
            "if official sources are insufficient, mark uncertainty and still finish the final report; "
            "workspace is cleared: do not reuse unrelated old findings/analysis/draft/report; "
            "after research_plan, you must web_search or delegate researcher; "
            "do not skip research and jump to drafting; "
            "after researcher writes findings, the main agent must not rewrite findings; "
            "analyst at most once; after analysis is written, the main agent must not rewrite analysis; "
            "editor at most once; after editor returns, revise draft at most once, then write the final report and stop; "
            "do not re-delegate editor; do not loop on edit/read of draft; "
            "do not delegate general-purpose; the main agent must draft the report; "
            "you must complete question, research_plan, findings, analysis (if comparison/numeric), "
            "draft, editor review, and final report."
        )
    
    run_result = await run_deep_agent_once(agent, user_prompt)

    return DeepAgentsRunResult(
        final_text=run_result.final_text,
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
            "todos": run_result.todos,
            "todos_export_path": run_result.todos_export_path,

            "analyst_calls": delegation_budget.analyst_calls,
            "editor_calls": delegation_budget.editor_calls,
            "analyst_call_limit": delegation_budget.max_analyst,
            "editor_call_limit": delegation_budget.max_editor,

            "usage": run_result.usage,
        },
    )


