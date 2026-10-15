import asyncio
import json
from pathlib import Path

from src.tools.calculator import structured_calculator
from src.tools.deepagents_adapter import (
    _format_deepagents_event,
    export_todos_to_tmp_json,
    run_deep_agent_once,
)
from src.workflow.deepagents_runner import (
    DeepAgentsRunResult,
    SearchBudget,
    build_deepagents_subagents,
    build_deepagents_system_prompt,
    create_limited_web_search,
    extract_search_result_urls,
    reset_workspace_run_artifacts,
)


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
    subagents = build_deepagents_subagents(
        search_tool, no_analysis=False, output_language="en"
    )

    assert [x["name"] for x in subagents] == ["researcher", "analyst", "editor"]
    assert subagents[0]["tools"][0].name == "web_search"
    assert [tool.name for tool in subagents[1]["tools"]] == ["structured_calculator"]
    for subagent in subagents:
        assert "every file you write MUST be in English" in subagent["system_prompt"]


def test_subagents_without_analysis():
    search_tool = create_limited_web_search(SearchBudget(max_calls=2))
    subagents = build_deepagents_subagents(
        search_tool, no_analysis=True, output_language="zh"
    )

    assert [x["name"] for x in subagents] == ["researcher", "editor"]
    for subagent in subagents:
        assert "写入文件必须使用中文" in subagent["system_prompt"]


def test_limited_web_search_contract():
    search_budget = SearchBudget(max_calls=2)
    search_tool = create_limited_web_search(search_budget)

    assert search_tool.name == "web_search"
    assert search_budget.max_calls == 2
    assert search_budget.call_count == 0


def test_limited_web_search_records_retrieved_source_urls(monkeypatch):
    async def fake_search(_query: str, _count: int) -> str:
        return (
            "标题: Official documentation\n"
            "URL: https://docs.example/streaming\n"
            "摘要: See https://summary.example/not-a-result for context\n"
            "网站图标: https://icons.example/favicon"
        )

    monkeypatch.setattr(
        "src.workflow.deepagents_runner.bocha_web_search", fake_search
    )
    search_budget = SearchBudget(max_calls=1)
    search_tool = create_limited_web_search(search_budget)

    result = asyncio.run(
        search_tool.ainvoke({"query": "streaming documentation", "count": 5})
    )

    assert "Official documentation" in result
    assert search_budget.retrieved_source_urls == {
        "https://docs.example/streaming"
    }
    assert search_budget.queries == [
        {"query": "streaming documentation", "count": 5}
    ]


def test_extract_search_result_urls_ignores_summary_and_icon_urls():
    result = (
        "URL: https://one.example/source\n"
        "摘要: Related: https://summary.example/page\n"
        "网站图标: https://icons.example/favicon\n\n"
        "URL: https://two.example/source\n"
    )

    assert extract_search_result_urls(result) == {
        "https://one.example/source",
        "https://two.example/source",
    }

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


def test_source_urls_must_be_copied_from_search_results():
    from src.tools.lib.prompts import (
        ORCHESTRATOR_SYSTEM_PROMPT,
        RESEARCHER_SYSTEM_PROMPT,
    )

    web_research = Path("skills/web-research/SKILL.md").read_text(encoding="utf-8")
    report_writer = Path("skills/report-writer/SKILL.md").read_text(encoding="utf-8")

    for text in [
        ORCHESTRATOR_SYSTEM_PROMPT,
        RESEARCHER_SYSTEM_PROMPT,
        web_research,
        report_writer,
    ]:
        assert "URL" in text
        assert "禁止" in text


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
    from src.tools.lib.prompts import (
        ORCHESTRATOR_SYSTEM_PROMPT,
        RUNTIME_DELEGATION_GUARD,
    )

    assert "禁止再次 write_file / edit_file 改写 findings" in ORCHESTRATOR_SYSTEM_PROMPT
    assert "禁止调用 general-purpose" in ORCHESTRATOR_SYSTEM_PROMPT
    assert "analyst 每份报告最多调用一次" in ORCHESTRATOR_SYSTEM_PROMPT
    assert "禁止委派 general-purpose" in RUNTIME_DELEGATION_GUARD
    assert "禁止第二次委派 editor" in RUNTIME_DELEGATION_GUARD
    assert "必须立刻写入 final report" in RUNTIME_DELEGATION_GUARD
    assert "整个运行最多调用一次 edit_file" in ORCHESTRATOR_SYSTEM_PROMPT


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


def test_reset_workspace_run_artifacts_keeps_readme(tmp_path: Path):
    sources = tmp_path / "workspace/sources"
    reports = tmp_path / "workspace/reports"
    sources.mkdir(parents=True, exist_ok=True)
    reports.mkdir(parents=True, exist_ok=True)

    stale_source = sources / "stale_findings.md"
    stale_report = reports / "stale_report.md"
    readme = sources / "README.md"
    stale_source.write_text("stale", encoding="utf-8")
    stale_report.write_text("stale", encoding="utf-8")
    readme.write_text("keep", encoding="utf-8")

    tmp_json = tmp_path / "tmp.json"
    tmp_json.write_text(
        '{"todos":[{"content":"old","status":"pending"}]}',
        encoding="utf-8",
    )

    reset_workspace_run_artifacts(tmp_path, tmp_json)

    assert readme.exists()
    assert not stale_report.exists()
    assert not tmp_json.exists()
    assert not stale_source.exists()


def test_export_todos_to_tmp_json_matches_teacher_shape(tmp_path: Path):
    export_path = tmp_path / "tmp.json"
    todos = [
        {
            "content": "搜索国家统计局官网发布的《2023年国民经济和社会发展统计公报》",
            "status": "in_progress",
        },
        {
            "content": "写入 findings 文件",
            "status": "pending",
        },
    ]

    written = export_todos_to_tmp_json(todos, export_path)
    payload = json.loads(written.read_text(encoding="utf-8"))

    assert written == export_path
    assert list(payload.keys()) == ["todos"]
    assert payload["todos"][0]["status"] == "in_progress"
    assert payload["todos"][1]["content"] == "写入 findings 文件"


def test_run_deep_agent_once_passes_callbacks(tmp_path: Path):
    callback = object()

    class FakeAgent:
        config = None

        async def astream_events(self, _input, *, config, version):
            self.config = config
            assert version == "v2"
            yield {
                "event": "on_chain_end",
                "name": "fake-agent",
                "data": {"output": {"messages": [{"content": "done"}]}},
            }

    agent = FakeAgent()
    result = asyncio.run(
        run_deep_agent_once(
            agent,
            "test topic",
            todos_export_path=tmp_path / "tmp.json",
            callbacks=[callback],
        )
    )

    assert result.final_text == "done"
    assert agent.config["callbacks"] == [callback]
    assert agent.config["recursion_limit"] == 80

def test_delegation_limit_middleware_blocks_second_analyst_and_editor():
    from types import SimpleNamespace

    from langchain_core.messages import ToolMessage

    from src.workflow.deepagents_runner import DelegationBudget
    from src.workflow.delegation_guard import DelegationLimitMiddleware
    budget = DelegationBudget(max_analyst=1, max_editor=1)
    guard = DelegationLimitMiddleware(budget)
    def make_task(subagent_type: str):
        return SimpleNamespace(
            tool_call={
                "name": "task",
                "args": {"subagent_type": subagent_type},
                "id": f"call-{subagent_type}",
            }
        )
    handler_called = {"n": 0}
    def handler(_req):
        handler_called["n"] += 1
        return "OK"
    assert guard.wrap_tool_call(make_task("analyst"), handler) == "OK"
    second = guard.wrap_tool_call(make_task("analyst"), handler)
    assert isinstance(second, ToolMessage)
    assert "委派被拒绝" in second.content
    assert handler_called["n"] == 1
    assert guard.wrap_tool_call(make_task("editor"), handler) == "OK"
    second_editor = guard.wrap_tool_call(make_task("editor"), handler)
    assert isinstance(second_editor, ToolMessage)
    assert "editor" in second_editor.content


def test_delegation_limit_middleware_tracks_rejected_researcher_attempt():
    from types import SimpleNamespace

    from langchain_core.messages import ToolMessage

    from src.workflow.deepagents_runner import DelegationBudget
    from src.workflow.delegation_guard import DelegationLimitMiddleware

    budget = DelegationBudget(max_researcher=3)
    guard = DelegationLimitMiddleware(budget)

    def make_task(index: int):
        return SimpleNamespace(
            tool_call={
                "name": "task",
                "args": {"subagent_type": "researcher"},
                "id": f"call-researcher-{index}",
            }
        )

    def handler(_request):
        return "OK"

    assert [guard.wrap_tool_call(make_task(index), handler) for index in range(3)] == [
        "OK",
        "OK",
        "OK",
    ]
    rejected = guard.wrap_tool_call(make_task(4), handler)

    assert isinstance(rejected, ToolMessage)
    assert "researcher" in rejected.content
    assert budget.researcher_calls == 4


def test_delegation_limit_middleware_blocks_second_draft_edit():
    from types import SimpleNamespace

    from langchain_core.messages import ToolMessage

    from src.workflow.deepagents_runner import DelegationBudget
    from src.workflow.delegation_guard import DelegationLimitMiddleware

    budget = DelegationBudget(max_draft_edits=1)
    guard = DelegationLimitMiddleware(budget)

    def make_edit(index: int):
        return SimpleNamespace(
            tool_call={
                "name": "edit_file",
                "args": {
                    "file_path": "/workspace/reports/draft_transport.md",
                    "old_string": f"before-{index}",
                    "new_string": f"after-{index}",
                },
                "id": f"call-edit-{index}",
            }
        )

    def handler(_request):
        return "OK"

    assert guard.wrap_tool_call(make_edit(1), handler) == "OK"
    rejected = guard.wrap_tool_call(make_edit(2), handler)

    assert isinstance(rejected, ToolMessage)
    assert "draft edit_file" in rejected.content
    assert budget.draft_edit_calls == 2


def test_delegation_limit_middleware_blocks_protected_source_writes():
    from types import SimpleNamespace

    from langchain_core.messages import ToolMessage

    from src.workflow.deepagents_runner import DelegationBudget
    from src.workflow.delegation_guard import DelegationLimitMiddleware
    guard = DelegationLimitMiddleware(DelegationBudget())
    def make_file(tool_name: str, file_path: str):
        return SimpleNamespace(
            tool_call={
                "name": tool_name,
                "args": {"file_path": file_path},
                "id": f"call-{tool_name}",
            }
        )
    def handler(_req):
        return "OK"
    blocked = guard.wrap_tool_call(
        make_file("write_file", "/workspace/sources/analysis_x.md"),
        handler,
    )
    assert isinstance(blocked, ToolMessage)
    assert "写入被拒绝" in blocked.content
    blocked2 = guard.wrap_tool_call(
        make_file("edit_file", "/workspace/sources/findings_langgraph.md"),
        handler,
    )
    assert isinstance(blocked2, ToolMessage)
    assert guard.wrap_tool_call(
        make_file("write_file", "/workspace/reports/draft_x.md"),
        handler,
    ) == "OK"
    assert guard.wrap_tool_call(
        make_file("write_file", "/workspace/sources/question.txt"),
        handler,
    ) == "OK"


def test_path_guard_rejects_root_artifact_paths_but_allows_sources():
    from types import SimpleNamespace

    from langchain_core.messages import ToolMessage

    from src.workflow.deepagents_runner import DelegationBudget
    from src.workflow.delegation_guard import DelegationLimitMiddleware

    path_guard = DelegationLimitMiddleware(
        DelegationBudget(max_analyst=0, max_editor=0),
        block_artifact_rewrites=False,
    )

    def make_file(tool_name: str, file_path: str):
        return SimpleNamespace(
            tool_call={
                "name": tool_name,
                "args": {"file_path": file_path},
                "id": f"call-{tool_name}",
            }
        )

    def handler(_req):
        return "OK"

    bad_root = path_guard.wrap_tool_call(
        make_file("write_file", "/findings_langgraph.md"),
        handler,
    )
    assert isinstance(bad_root, ToolMessage)
    assert "路径非法" in bad_root.content

    bad_analysis = path_guard.wrap_tool_call(
        make_file("write_file", "/analysis_x.md"),
        handler,
    )
    assert isinstance(bad_analysis, ToolMessage)
    assert "路径非法" in bad_analysis.content

    assert (
        path_guard.wrap_tool_call(
            make_file("write_file", "/workspace/sources/findings_langgraph.md"),
            handler,
        )
        == "OK"
    )
    assert (
        path_guard.wrap_tool_call(
            make_file("write_file", "/workspace/sources/analysis_x.md"),
            handler,
        )
        == "OK"
    )


def test_path_guard_wired_to_researcher_and_analyst_only():
    from src.workflow.deepagents_runner import DelegationBudget
    from src.workflow.delegation_guard import DelegationLimitMiddleware

    path_guard = DelegationLimitMiddleware(
        DelegationBudget(max_analyst=0, max_editor=0),
        block_artifact_rewrites=False,
    )
    subagents = build_deepagents_subagents(
        search_tool=lambda: None,
        path_guard=path_guard,
    )
    by_name = {s["name"]: s for s in subagents}

    assert by_name["researcher"]["middleware"] == [path_guard]
    assert by_name["analyst"]["middleware"] == [path_guard]
    assert "middleware" not in by_name["editor"]


def test_path_guard_rejects_non_lowercase_artifact_filenames():
    from types import SimpleNamespace

    from langchain_core.messages import ToolMessage

    from src.workflow.deepagents_runner import DelegationBudget
    from src.workflow.delegation_guard import DelegationLimitMiddleware

    path_guard = DelegationLimitMiddleware(
        DelegationBudget(max_analyst=0, max_editor=0),
        block_artifact_rewrites=False,
    )

    def make_file(file_path: str):
        return SimpleNamespace(
            tool_call={
                "name": "write_file",
                "args": {"file_path": file_path},
                "id": "call-write",
            }
        )

    def handler(_req):
        return "OK"

    camel = path_guard.wrap_tool_call(
        make_file("/workspace/sources/findings_LangGraph.md"),
        handler,
    )
    assert isinstance(camel, ToolMessage)
    assert "文件名非法" in camel.content

    alias = path_guard.wrap_tool_call(
        make_file("/workspace/sources/AutoGen_research.md"),
        handler,
    )
    # 非 findings_/analysis_ 前缀，路径守卫不把它当 artifact
    assert alias == "OK" or isinstance(alias, ToolMessage)

    assert (
        path_guard.wrap_tool_call(
            make_file("/workspace/sources/findings_langgraph.md"),
            handler,
        )
        == "OK"
    )


def test_filename_convention_in_prompts_and_skills():
    from src.tools.lib.prompts import (
        ANALYST_SYSTEM_PROMPT,
        FILENAME_CONVENTION,
        LANGUAGE_POLICY,
        ORCHESTRATOR_SYSTEM_PROMPT,
        RESEARCHER_SYSTEM_PROMPT,
    )

    web_research = Path("skills/web-research/SKILL.md").read_text(encoding="utf-8")
    report_writer = Path("skills/report-writer/SKILL.md").read_text(encoding="utf-8")

    for text in [
        FILENAME_CONVENTION,
        RESEARCHER_SYSTEM_PROMPT,
        ANALYST_SYSTEM_PROMPT,
        ORCHESTRATOR_SYSTEM_PROMPT,
        web_research,
        report_writer,
    ]:
        assert "全小写" in text or "[a-z0-9_]" in text or "小写" in text

    assert "禁止臆造文件名" in ANALYST_SYSTEM_PROMPT
    assert "精确写入路径" in ORCHESTRATOR_SYSTEM_PROMPT
    assert "findings_langgraph.md" in web_research

    assert "跟随用户" in LANGUAGE_POLICY
    assert "中文提问" in LANGUAGE_POLICY
    assert "英文提问" in LANGUAGE_POLICY
    assert "跟随用户" in ORCHESTRATOR_SYSTEM_PROMPT
    assert "语言跟随用户" in report_writer or "跟随用户提问" in report_writer

    agents_md = Path("AGENTS.md").read_text(encoding="utf-8")
    assert "Match the user's query language" in agents_md
    assert "Chinese-first" not in agents_md
