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

    def __init__(self, budget: Any, block_artifact_rewrites: bool = True):
        super().__init__()
        self.budget = budget
        self.block_artifact_rewrites = block_artifact_rewrites
    
    def _extract_file_path(self, args: dict) -> str:
        return str(
            args.get("file_path")
            or args.get("path")
            or args.get("filePath")
            or ""
        )
    def _artifact_write_error(self, file_path: str) -> str | None:
        """
        若不允许写入，返回错误文案；允许则返回 None。
        """

        normalized = file_path.replace("\\", "/")
        filename = normalized.rsplit("/", 1)[-1].lower()

        is_artifact = filename.startswith("findings_") or filename.startswith("analysis_")

        if not is_artifact:
            return None
        
        in_sources = "/workspace/sources/" in normalized or normalized.startswith("workspace/sources")

        if not self.block_artifact_rewrites:
            if not in_sources:
                return (
                    f"路径非法：`{file_path}`。"
                    "findings_/analysis_ 必须写到 `/workspace/sources/` 下，"
                    "例如 `/workspace/sources/findings_langgraph.md`。"
                    "禁止写到 `/findings_xxx.md` 这种根路径。"
                )
            
            return None
        
        return (
            f"写入被拒绝：主 Agent 禁止修改受保护文件 `{file_path}`。"
            "findings/analysis 应由子 Agent 写入 `/workspace/sources/`；"
            "主 Agent 只读，然后起草 `/workspace/reports/` 下的 draft/report。"
        )
        

    
    def _is_protected_source_file(self, file_path: str) -> bool:
        normalized = file_path.replace("\\", "/")
        name = normalized.rsplit("/", 1)[-1].lower()

        return name.startswith("findings_") or name.startswith("analysis_")
    
    def _check_or_reject(self, request: ToolCallRequest) -> ToolMessage | None:
        tool_call = request.tool_call or {}
        name = tool_call.get("name")
        
        args = tool_call.get("args") or {}
        tool_call_id = tool_call.get("id") or ""

        if name in {"write_file", "edit_file"}:
            file_path = self._extract_file_path(args)
            err = self._artifact_write_error(file_path)
            if err:
                print(f"[guard] blocked {name} path={file_path!r}")
                return ToolMessage(
                    content=err,
                    tool_call_id=tool_call_id,
                    name=name,
                    status="error",
                )
            return None
        if name == "task":
            subagent_type = args.get("subagent_type") or args.get("subagent") or ""

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

        rejected = self._check_or_reject(request)
        if rejected is not None:
            print(f"[guard] blocked task subagent={ (request.tool_call or {}).get('args', {}).get('subagent_type') }")
            return rejected
        
        return handler(request)
    
    async def awrap_tool_call(
        self,
        request: ToolCallRequest,
        handler: Callable[[ToolCallRequest], Any]
    ) -> Any:
        rejected = self._check_or_reject(request)
        if rejected is not None:
            print(f"[guard] blocked task subagent={ (request.tool_call or {}).get('args', {}).get('subagent_type') }")
            return rejected
        
        return await handler(request)



