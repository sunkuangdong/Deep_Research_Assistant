from types import SimpleNamespace

from langchain_core.messages import ToolMessage

from src.workflow.deepagents_runner import DelegationBudget
from src.workflow.delegation_guard import DelegationLimitMiddleware


def make_request(subagent_type: str):
    return SimpleNamespace(
        tool_call={
            "name": "task",
            "args": {"subagent_type": subagent_type},
            "id": f"call-{subagent_type}",
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


if __name__ == "__main__":
    main()
