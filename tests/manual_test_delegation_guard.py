from types import SimpleNamespace

from langchain_core.messages import ToolMessage

from src.workflow.deepagents_runner import DelegationBudget, build_deepagents_subagents
from src.workflow.delegation_guard import DelegationLimitMiddleware


def make_request(subagent_type: str):
    return SimpleNamespace(
        tool_call={
            "name": "task",
            "args": {"subagent_type": subagent_type},
            "id": f"call-{subagent_type}",
        }
    )

def make_file_request(tool_name: str, file_path: str):
    return SimpleNamespace(
        tool_call={
            "name": tool_name,
            "args": {"file_path": file_path},
            "id": f"call-{tool_name}",
        }
    )


def main() -> None:
    budget = DelegationBudget(max_analyst=1, max_editor=1)
    guard = DelegationLimitMiddleware(budget)

    handler_called = {"n": 0}

    def handler(_req):
        handler_called["n"] += 1
        return "OK"

    # 1) 第一次 analyst：放行
    assert guard.wrap_tool_call(make_request("analyst"), handler) == "OK"
    assert budget.analyst_calls == 1
    assert handler_called["n"] == 1

    # 2) 第二次 analyst：拦截
    r2 = guard.wrap_tool_call(make_request("analyst"), handler)
    assert isinstance(r2, ToolMessage)
    assert "委派被拒绝" in r2.content
    assert budget.analyst_calls == 1
    assert handler_called["n"] == 1

    # 3) editor 同理
    assert guard.wrap_tool_call(make_request("editor"), handler) == "OK"
    assert budget.editor_calls == 1

    r4 = guard.wrap_tool_call(make_request("editor"), handler)
    assert isinstance(r4, ToolMessage)
    assert "editor" in r4.content
    assert budget.editor_calls == 1

    # 4) researcher 本步不限制
    assert guard.wrap_tool_call(make_request("researcher"), handler) == "OK"

    print("硬限制第 1 步单元测试 OK")

    # 禁止写 analysis
    blocked = guard.wrap_tool_call(
        make_file_request("write_file", "/workspace/sources/analysis_x.md"),
        handler,
    )
    assert isinstance(blocked, ToolMessage)
    assert "写入被拒绝" in blocked.content
    # 禁止 edit findings
    blocked2 = guard.wrap_tool_call(
        make_file_request("edit_file", "/workspace/sources/findings_langgraph.md"),
        handler,
    )
    assert isinstance(blocked2, ToolMessage)
    # 允许写 draft
    assert guard.wrap_tool_call(
        make_file_request("write_file", "/workspace/reports/draft_x.md"),
        handler,
    ) == "OK"
    # 允许写 question
    assert guard.wrap_tool_call(
        make_file_request("write_file", "/workspace/sources/question.txt"),
        handler,
    ) == "OK"

    # 子 Agent 路径模式：拦根路径，放行 /workspace/sources/
    path_guard = DelegationLimitMiddleware(
        DelegationBudget(max_analyst=0, max_editor=0),
        block_artifact_rewrites=False,
    )
    bad = path_guard.wrap_tool_call(
        make_file_request("write_file", "/findings_langgraph.md"),
        handler,
    )
    assert isinstance(bad, ToolMessage)
    assert "路径非法" in bad.content
    assert (
        path_guard.wrap_tool_call(
            make_file_request("write_file", "/workspace/sources/findings_langgraph.md"),
            handler,
        )
        == "OK"
    )
    assert (
        path_guard.wrap_tool_call(
            make_file_request("write_file", "/workspace/sources/analysis_x.md"),
            handler,
        )
        == "OK"
    )

    # CamelCase / 非法 slug 文件名应被硬拦截
    camel = path_guard.wrap_tool_call(
        make_file_request("write_file", "/workspace/sources/findings_LangGraph.md"),
        handler,
    )
    assert isinstance(camel, ToolMessage)
    assert "文件名非法" in camel.content

    # wiring：researcher / analyst 挂 path_guard，editor 不挂
    subs = build_deepagents_subagents(search_tool=lambda: None, path_guard=path_guard)
    by_name = {s["name"]: s for s in subs}
    assert by_name["researcher"]["middleware"] == [path_guard]
    assert by_name["analyst"]["middleware"] == [path_guard]
    assert "middleware" not in by_name["editor"]

    print("路径校验第 1 步单元测试 OK")


if __name__ == "__main__":
    main()

