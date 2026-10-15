from __future__ import annotations

import asyncio
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from langchain_core.tools import tool

from src.tools.calculator import structured_calculator
from src.tools.deepagents_adapter import (
    DEFAULT_TODOS_EXPORT_PATH,
    DeepAgentBuildConfig,
    build_deep_agent,
    run_deep_agent_once,
)
from src.tools.lib.prompts import (
    ANALYST_SYSTEM_PROMPT,
    DEEPAGENTS_ORCHESTRATION_GUARD,
    EDITOR_SYSTEM_PROMPT,
    ORCHESTRATOR_SYSTEM_PROMPT,
    RESEARCHER_SYSTEM_PROMPT,
    RUNTIME_ANALYSIS_REQUIREMENT,
    RUNTIME_DELEGATION_GUARD,
    RUNTIME_NO_ANALYSIS_GUARD,
)
from src.tools.search import (
    WebFetchInput,
    WebSearchInput,
    bocha_web_search,
    canonical_source_url,
    fetch_web_page,
)
from src.workflow.delegation_guard import DelegationLimitMiddleware


class SearchBudget:
    def __init__(self, max_calls: int, max_fetch_calls: int = 6):
        self.max_calls = max_calls
        self.call_count = 0
        self.max_fetch_calls = max_fetch_calls
        self.fetch_call_count = 0
        self.fetch_attempt_count = 0
        self.fetch_duplicate_rejections = 0
        self.fetch_budget_rejections = 0
        self.search_result_urls: set[str] = set()
        self.fetched_source_urls: set[str] = set()
        self.fetched_source_pages: set[str] = set()
        self.retrieved_source_urls: set[str] = set()
        self.queries: list[dict[str, Any]] = []
        self.fetch_requests: list[str] = []


SEARCH_RESULT_URL_RE = re.compile(
    r"^\s*URL:\s*(https?://\S+)\s*$", re.IGNORECASE | re.MULTILINE
)
FETCHED_URL_RE = re.compile(
    r"^\s*Fetched URL:\s*(https?://\S+)\s*$", re.IGNORECASE | re.MULTILINE
)


def extract_search_result_urls(result: str) -> set[str]:
    """Extract only explicit result URL fields, excluding summary and icon URLs."""

    return {match.group(1) for match in SEARCH_RESULT_URL_RE.finditer(result)}


def extract_fetched_source_urls(result: str) -> set[str]:
    """Extract only URLs from successful web_fetch responses."""

    return {match.group(1) for match in FETCHED_URL_RE.finditer(result)}
    
class DelegationBudget:
    def __init__(
        self,
        max_researcher: int = 3,
        max_analyst: int = 1,
        max_editor: int = 1,
        max_draft_edits: int = 1,
    ):
        self.max_researcher = max_researcher
        self.max_analyst = max_analyst
        self.max_editor = max_editor
        self.max_draft_edits = max_draft_edits
        self.researcher_calls = 0
        self.analyst_calls = 0
        self.editor_calls = 0
        self.draft_edit_calls = 0
        self.researcher_attempts = 0
        self.analyst_attempts = 0
        self.editor_attempts = 0
        self.draft_edit_attempts = 0
        self.researcher_rejections = 0
        self.analyst_rejections = 0
        self.editor_rejections = 0
        self.draft_edit_rejections = 0

def reset_workspace_run_artifacts(
    root_dir: Path | str = ".",
    todos_export_path: Path | str | None = None,
) -> None:
    """
    清理上一次运行留下的过程文件，避免 Agent 误用旧 findings / 旧计划。
    保留 README.md 与 .gitkeep。
    """
    keep_names = {".gitkeep", "README.md"}

    root_path = Path(root_dir)
    for folder in (
        root_path / "workspace/sources",
        root_path / "workspace/reports",
    ):
        if not folder.exists():
            continue

        for file_path in folder.iterdir():
            if not file_path.is_file() or file_path.name in keep_names:
                continue
            file_path.unlink()

    export_path = (
        Path(todos_export_path)
        if todos_export_path is not None
        else root_path / DEFAULT_TODOS_EXPORT_PATH
    )
    if export_path.exists():
        export_path.unlink()

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
        search_budget.queries.append({"query": query, "count": safe_count})

        print(
            f"  🔎 搜索[{search_budget.call_count}/{search_budget.max_calls}]: "
            f"{query}（{safe_count} 条）"
        )
        
        result = await bocha_web_search(query, safe_count)
        result_urls = extract_search_result_urls(result)
        search_budget.search_result_urls.update(result_urls)
        search_budget.retrieved_source_urls.update(result_urls)
        return result

    return limited_web_search


def create_limited_web_fetch(search_budget: SearchBudget) -> Any:
    """Create a bounded fetch tool that records only successfully fetched URLs."""

    reservation_lock = asyncio.Lock()
    reserved_pages: set[str] = set()

    @tool("web_fetch", args_schema=WebFetchInput)
    async def limited_web_fetch(url: str) -> str:
        """读取并验证公开 HTTP(S) 文本页面，并限制单次运行的抓取次数。"""

        requested_page = canonical_source_url(url)
        async with reservation_lock:
            search_budget.fetch_attempt_count += 1
            if requested_page in reserved_pages:
                search_budget.fetch_duplicate_rejections += 1
                existing_pages = ", ".join(sorted(reserved_pages))
                return (
                    "DUPLICATE_FETCH: This page was already fetched or is being "
                    "fetched in this run. URL fragments do not create a distinct "
                    f"source. Existing pages: {existing_pages}. This duplicate did "
                    "not consume the shared fetch budget. Choose an official page "
                    "with a different host/path and call web_fetch again."
                )
            if search_budget.fetch_call_count >= search_budget.max_fetch_calls:
                search_budget.fetch_budget_rejections += 1
                return (
                    f"web_fetch 抓取预算已用完。本次最多允许 "
                    f"{search_budget.max_fetch_calls} 次抓取，请基于已有证据继续。"
                )
            reserved_pages.add(requested_page)
            search_budget.fetch_call_count += 1
            search_budget.fetch_requests.append(url)

        print(
            f"  🌐 抓取[{search_budget.fetch_call_count}/"
            f"{search_budget.max_fetch_calls}]: {url}"
        )
        result = await fetch_web_page(url)
        fetched_urls = extract_fetched_source_urls(result)
        if not fetched_urls:
            async with reservation_lock:
                reserved_pages.discard(requested_page)
            return result

        fetched_pages = {canonical_source_url(value) for value in fetched_urls}
        async with reservation_lock:
            reserved_pages.update(fetched_pages)
        search_budget.fetched_source_urls.update(fetched_urls)
        search_budget.fetched_source_pages.update(fetched_pages)
        search_budget.retrieved_source_urls.update(fetched_urls)
        return result

    return limited_web_fetch



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

def _subagent_language_instruction(output_language: str) -> str:
    if output_language == "zh":
        return (
            "\n\n[本次运行语言硬约束]\n"
            "- 用户使用中文提问。你的回复、研究或分析内容、审阅意见及写入文件必须使用中文。\n"
            "- 专有名词、模型名、库名和 URL 可以保留原文。"
        )
    return (
        "\n\n[Run Language Constraint]\n"
        "- The user asked in English. Your response, research or analysis content, "
        "review comments, and every file you write MUST be in English.\n"
        "- Proper nouns, model names, library names, and URLs may remain unchanged."
    )


def build_deepagents_subagents(
    search_tool,
    fetch_tool=None,
    no_analysis: bool = False,
    path_guard=None,
    output_language: str = "en",
) -> list[Any]:
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
    language_instruction = _subagent_language_instruction(output_language)
    researcher_tools = [search_tool]
    if fetch_tool is not None:
        researcher_tools.append(fetch_tool)

    subagents = [
        {
            "name": "researcher",
            "description": (
                "Use this subagent for focused web research on one specific "
                "subtopic. It can search the web and return evidence with URLs."
            ),
            "system_prompt": (
                RESEARCHER_SYSTEM_PROMPT.strip()
                + language_instruction
                + "\n\n[Search Budget]\n"
                + "- You may call web_search at most 2 times for one delegated subtopic.\n"
                + "- You may call web_fetch at most 2 times for one delegated subtopic.\n"
                + "- If search misses a known official page, use web_fetch to retrieve and verify its exact URL.\n"
                + "- URL fragments identify sections, not distinct source pages. If web_fetch reports DUPLICATE_FETCH, choose a different official page path.\n"
                + "- Use focused queries, not many small wording variations.\n"
                + "- Stop searching once you have enough evidence.\n"
                + "- Return concise findings with source URLs.\n"
            ),
            "tools": researcher_tools,
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
                "system_prompt": ANALYST_SYSTEM_PROMPT + language_instruction,
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
            "system_prompt": EDITOR_SYSTEM_PROMPT + language_instruction,
            "tools": [],
        }
    )

    return subagents

async def run_deepagents_workflow(
    topic: str,
    no_analysis: bool = False,
    root_dir: Path | str = ".",
    todos_export_path: Path | str | None = None,
    callbacks: list[Any] | None = None,
    run_date: str | None = None,
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
    use_chinese = any("\u4e00" <= ch <= "\u9fff" for ch in clean_topic)
    output_language = "zh" if use_chinese else "en"

    path_guard = DelegationLimitMiddleware(
        DelegationBudget(
            max_researcher=0,
            max_analyst=0,
            max_editor=0,
            max_draft_edits=0,
        ),
        block_artifact_rewrites=False,
    )

    root_path = Path(root_dir).resolve()
    resolved_todos_path = (
        Path(todos_export_path)
        if todos_export_path is not None
        else root_path / DEFAULT_TODOS_EXPORT_PATH
    )
    reset_workspace_run_artifacts(root_path, resolved_todos_path)
    system_prompt = build_deepagents_system_prompt(no_analysis=no_analysis)
    effective_run_date = run_date or datetime.now().astimezone().date().isoformat()
    search_budget = SearchBudget(max_calls=6, max_fetch_calls=6)
    search_tool = create_limited_web_search(search_budget)
    fetch_tool = create_limited_web_fetch(search_budget)

    subagents = build_deepagents_subagents(
        search_tool,
        fetch_tool,
        no_analysis=no_analysis,
        path_guard=path_guard,
        output_language=output_language,
    )

    delegation_budget = DelegationBudget(
        max_researcher=3,
        max_analyst=1,
        max_editor=1,
        max_draft_edits=1,
    )
    main_guard = DelegationLimitMiddleware(delegation_budget, block_artifact_rewrites=True)

    config = DeepAgentBuildConfig(
        root_dir=str(root_path),
        skills=["./skills"],
        memory=["./AGENTS.md"],
        system_prompt=system_prompt,
        debug=False,
        name="deep_research_agent",
        tools=[search_tool, fetch_tool],
        subagents=subagents,
        middleware=[main_guard],
    )

    agent = build_deep_agent(config)

    if no_analysis:
        analysis_rule_zh = (
            "本次已启用 no-analysis：禁止委派 analyst，禁止创建或写入 analysis 文件；"
            "读取 findings 后直接起草 draft。必须完成 question、research_plan、findings、"
            "draft、editor 审阅和 final report。"
        )
        analysis_rule_en = (
            "This run uses no-analysis: do not delegate analyst and do not create or write "
            "an analysis file. After reading findings, proceed directly to the draft. "
            "You must complete question, research_plan, findings, draft, editor review, "
            "and final report."
        )
    else:
        analysis_rule_zh = (
            "analyst 最多调用 1 次，写完 analysis 后禁止主 Agent 再改 analysis；"
            "必须完成 question、research_plan、findings、analysis（如涉及对比/数值）、"
            "draft、editor 审阅和 final report。"
        )
        analysis_rule_en = (
            "Delegate analyst at most once; after analysis is written, the main agent must "
            "not rewrite it. You must complete question, research_plan, findings, analysis "
            "(if comparison/numeric), draft, editor review, and final report."
        )

    if use_chinese:
        user_prompt = (
            f"请围绕这个主题完成调研并给出最终报告：{clean_topic}\n\n"
            f"运行日期：{effective_run_date}。报告文件名中的日期必须使用这个运行日期，禁止自行编造日期。\n"
            "【语言】用户用中文提问，因此 todo、findings、启用时的 analysis、draft、report、最终回复都必须使用中文；"
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
            "editor 最多调用 1 次；editor 返回后最多修订 draft 一次，然后必须立刻写入 final report 并结束；"
            "整个运行最多调用 1 次 edit_file 修改 draft；必须把所有修改合并到这一次调用中，禁止拆成多次 edit_file；"
            "禁止二次委派 editor，禁止在 draft 上反复 edit/read 空转；"
            "禁止委派 general-purpose；报告起草必须由主 Agent 自己完成；"
            f"{analysis_rule_zh}"
        )
    else:
        user_prompt = (
            f"Please research this topic and produce a final report: {clean_topic}\n\n"
            f"Run date: {effective_run_date}. The date in the report filename MUST use this run date; do not invent dates.\n"
            "[Language] The user asked in English, so todos, findings, analysis when enabled, draft, report, "
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
            "editor at most once; after editor returns, revise draft at most once, then write the final report and stop; "
            "across the entire run, call edit_file on the draft at most once; combine all draft changes into that single call; "
            "do not re-delegate editor; do not loop on edit/read of draft; "
            "do not delegate general-purpose; the main agent must draft the report; "
            f"{analysis_rule_en}"
        )
    
    run_result = await run_deep_agent_once(
        agent,
        user_prompt,
        todos_export_path=resolved_todos_path,
        callbacks=callbacks,
    )

    return DeepAgentsRunResult(
        final_text=run_result.final_text,
        metadata={
            "runtime": "deepagents",
            "skills": ["./skills"],
            "memory": ["./AGENTS.md"],
            "subagents": [x["name"] for x in subagents],
            "no_analysis": no_analysis,
            "analysis_enabled": not no_analysis,
            "run_date": effective_run_date,
            "search_calls": search_budget.call_count,
            "search_call_limit": search_budget.max_calls,
            "search_queries": search_budget.queries,
            "fetch_calls": search_budget.fetch_call_count,
            "fetch_call_limit": search_budget.max_fetch_calls,
            "fetch_attempts": search_budget.fetch_attempt_count,
            "fetch_duplicate_rejections": search_budget.fetch_duplicate_rejections,
            "fetch_budget_rejections": search_budget.fetch_budget_rejections,
            "fetch_requests": search_budget.fetch_requests,
            "search_result_urls": sorted(search_budget.search_result_urls),
            "fetched_source_urls": sorted(search_budget.fetched_source_urls),
            "fetched_source_pages": sorted(search_budget.fetched_source_pages),
            "retrieved_source_urls": sorted(search_budget.retrieved_source_urls),
            "workspace": "/workspace",
            "workspace_sources": "/workspace/sources",
            "workspace_reports": "/workspace/reports",
            "expected_report_glob": "/workspace/reports/report_*.md",
            "todos": run_result.todos,
            "todos_export_path": run_result.todos_export_path,

            "researcher_calls": delegation_budget.researcher_calls,
            "analyst_calls": delegation_budget.analyst_calls,
            "editor_calls": delegation_budget.editor_calls,
            "draft_edit_calls": delegation_budget.draft_edit_calls,
            "researcher_attempts": delegation_budget.researcher_attempts,
            "analyst_attempts": delegation_budget.analyst_attempts,
            "editor_attempts": delegation_budget.editor_attempts,
            "draft_edit_attempts": delegation_budget.draft_edit_attempts,
            "researcher_rejections": delegation_budget.researcher_rejections,
            "analyst_rejections": delegation_budget.analyst_rejections,
            "editor_rejections": delegation_budget.editor_rejections,
            "draft_edit_rejections": delegation_budget.draft_edit_rejections,
            "researcher_call_limit": delegation_budget.max_researcher,
            "analyst_call_limit": delegation_budget.max_analyst,
            "editor_call_limit": delegation_budget.max_editor,
            "draft_edit_call_limit": delegation_budget.max_draft_edits,

            "usage": run_result.usage,
        },
    )


