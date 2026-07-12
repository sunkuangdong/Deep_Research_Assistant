from __future__ import annotations

from typing import Any, Callable

from langchain.agents.middleware import AgentMiddleware
from langchain_core.messages import ToolMessage
from langgraph.prebuilt.tool_node import ToolCallRequest

class DelegationLimitMiddleware(AgentMiddleware):
    """
    硬限制主 Agent 的 task 委派次数：
    - analyst 最多 N 次
    - editor 最多 M 次
    超限时不真正调用子 Agent，直接返回拒绝 ToolMessage。
    """

    def __init__(self, budget: any):
        super().__init__()
        self.budget = budget
    
    def _check_or_rehect(self, request: ToolCallRequest) -> ToolMessage | None:
        tool_call = request.tool_call or {}
        name = tool_call.get("name")
        if name != "task":
            return None
        
        args = tool_call.get("args") or {}
        subagent_type = args.get("subagent_type") or args.get("subagent") or ""
        tool_call_id = tool_call.get("id") or ""

        if subagent_type == "analyst":
            if self.budget.analyst_calls >= self.budget.max_analyst:
                return ToolMessage(
                    content=(
                        f"委派被拒绝：analyst 最多允许 {self.budget.max_analyst} 次。"
                        "请基于已有 analysis 继续起草 draft，不要再次委派 analyst。"
                    ),
                    tool_call_id=tool_call_id,
                    name="task",
                    status="error",
                )
            self.budget.analyst_calls += 1
            return None
        
        if subagent_type == "editor":
            if self.budget.editor_calls >= self.budget.max_editor:
                return ToolMessage(
                    content=(
                        f"委派被拒绝：editor 最多允许 {self.budget.max_editor} 次。"
                        "请根据已有审阅意见修订 draft，并立刻写入 final report。"
                    ),
                    tool_call_id=tool_call_id,
                    name="task",
                    status="error",
                )
            self.budget.editor_calls += 1
            return None
        
        return None

    def wrap_tool_call(
        self, 
        request: ToolCallRequest,
        handler: Callable[[ToolCallRequest], Any]
    ) -> Any:

        rejected = self._check_or_rehect(request)
        if rejected is not None:
            print(f"[guard] blocked task subagent={ (request.tool_call or {}).get('args', {}).get('subagent_type') }")
            return rejected
        
        return handler(request)
    
    async def awrap_tool_call(
        self,
        request: ToolCallRequest,
        handler: Callable[[ToolCallRequest], Any]
    ) -> Any:
        rejected = self._check_or_rehect(request)
        if rejected is not None:
            print(f"[guard] blocked task subagent={ (request.tool_call or {}).get('args', {}).get('subagent_type') }")
            return rejected
        
        return await handler(request)



