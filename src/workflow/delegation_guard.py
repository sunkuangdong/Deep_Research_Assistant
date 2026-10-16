from __future__ import annotations

import re
from collections.abc import Callable
from typing import Any

from langchain.agents.middleware import AgentMiddleware
from langchain_core.messages import ToolMessage
from langgraph.prebuilt.tool_node import ToolCallRequest

# findings_langgraph.md / analysis_langgraph_vs_autogen.md
ARTIFACT_FILENAME_RE = re.compile(r"^(findings|analysis)_[a-z0-9][a-z0-9_-]*\.md$")
DRAFT_FILENAME_RE = re.compile(r"^draft_[a-z0-9][a-z0-9_-]*\.md$")
REPORT_FILENAME_RE = re.compile(
    r"^report_[a-z0-9][a-z0-9_-]*_\d{4}-\d{2}-\d{2}\.md$"
)
RECOVERY_MARKER = "[EVIDENCE_RECOVERY]"
TASK_FINDINGS_PATH_RE = re.compile(
    r"(?:/)?workspace/sources/(findings_[a-z0-9][a-z0-9_-]*\.md)"
)


class DelegationLimitMiddleware(AgentMiddleware):
    """
    硬限制主 Agent 的 task 委派次数：
    - researcher / analyst / editor 各自最多允许 N 次
    - draft 最多允许配置数量的 edit_file 调用
    超限时不真正调用子 Agent，直接返回拒绝 ToolMessage。
    同时校验 findings_/analysis_ 的路径与小写 slug 文件名。
    """

    def __init__(
        self,
        budget: Any,
        block_artifact_rewrites: bool = True,
        evidence_inventory: Any | None = None,
        search_budget: Any | None = None,
    ):
        super().__init__()
        self.budget = budget
        self.block_artifact_rewrites = block_artifact_rewrites
        self.evidence_inventory = evidence_inventory
        self.search_budget = search_budget
    
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
        raw_filename = normalized.rsplit("/", 1)[-1]
        filename = raw_filename.lower()

        is_artifact = filename.startswith(("findings_", "analysis_"))

        if not is_artifact:
            return None

        if not ARTIFACT_FILENAME_RE.match(raw_filename):
            return (
                f"文件名非法：`{file_path}`。"
                "findings_/analysis_ 必须全小写 ASCII slug，"
                "例如 `/workspace/sources/findings_langgraph.md`、"
                "`/workspace/sources/analysis_langgraph_vs_autogen.md`。"
                "禁止 CamelCase、空格，或 `*_research.md` 这类别名。"
            )
        
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

        return name.startswith(("findings_", "analysis_"))

    def _is_draft_file(self, file_path: str) -> bool:
        normalized = file_path.replace("\\", "/")
        filename = normalized.rsplit("/", 1)[-1]
        in_reports = "/workspace/reports/" in normalized or normalized.startswith(
            "workspace/reports/"
        )
        return in_reports and bool(DRAFT_FILENAME_RE.match(filename))

    def _is_report_file(self, file_path: str) -> bool:
        normalized = file_path.replace("\\", "/")
        filename = normalized.rsplit("/", 1)[-1]
        in_reports = "/workspace/reports/" in normalized or normalized.startswith(
            "workspace/reports/"
        )
        return in_reports and bool(REPORT_FILENAME_RE.match(filename))

    def _extract_file_content(self, args: dict) -> str:
        return str(args.get("content") or args.get("text") or "")

    def _evidence_gate_or_reject(
        self,
        *,
        stage: str,
        tool_call_id: str,
        tool_name: str,
        output_text: str | None = None,
        enforce_output_citations: bool = False,
    ) -> ToolMessage | None:
        if self.evidence_inventory is None:
            return None
        result = self.evidence_inventory.evaluate_gate(
            stage,
            output_text=output_text,
            enforce_output_citations=enforce_output_citations,
        )
        if result.passed:
            return None
        print(
            f"[evidence-gate] blocked {stage} "
            f"eligible={result.snapshot.eligible_count}/"
            f"{result.snapshot.minimum_citations}"
        )
        return ToolMessage(
            content=result.message,
            tool_call_id=tool_call_id,
            name=tool_name,
            status="error",
        )

    def _count_or_reject(
        self,
        *,
        counter_name: str,
        limit_name: str,
        label: str,
        tool_call_id: str,
        tool_name: str,
        guidance: str,
    ) -> ToolMessage | None:
        attempts_name = counter_name.replace("_calls", "_attempts")
        rejections_name = counter_name.replace("_calls", "_rejections")
        attempts = int(getattr(self.budget, attempts_name, 0)) + 1
        setattr(self.budget, attempts_name, attempts)
        calls = int(getattr(self.budget, counter_name, 0))
        limit = int(getattr(self.budget, limit_name, 0))
        if calls >= limit:
            rejections = int(getattr(self.budget, rejections_name, 0)) + 1
            setattr(self.budget, rejections_name, rejections)
            action = "委派" if tool_name == "task" else "调用"
            return ToolMessage(
                content=(
                    f"{action}被拒绝：{label} 最多允许 {limit} 次，"
                    f"本次是第 {attempts} 次尝试。{guidance}"
                ),
                tool_call_id=tool_call_id,
                name=tool_name,
                status="error",
            )
        setattr(self.budget, counter_name, calls + 1)
        return None

    def _researcher_rejection(
        self,
        *,
        message: str,
        tool_call_id: str,
        recovery_attempt: bool = False,
    ) -> ToolMessage:
        self.budget.researcher_rejections += 1
        if recovery_attempt:
            self.budget.researcher_recovery_rejections += 1
        return ToolMessage(
            content=message,
            tool_call_id=tool_call_id,
            name="task",
            status="error",
        )

    def _researcher_or_reject(
        self,
        *,
        args: dict,
        tool_call_id: str,
    ) -> ToolMessage | None:
        """Enforce structured planning and preserve the final recovery slot."""

        self.budget.researcher_attempts += 1
        calls = int(self.budget.researcher_calls)
        limit = int(self.budget.max_researcher)
        reserved = int(getattr(self.budget, "reserved_researcher_calls", 0))
        initial_limit = max(0, limit - reserved)

        if calls >= limit:
            return self._researcher_rejection(
                message=(
                    f"委派被拒绝：researcher 最多允许 {limit} 次，本次是第 "
                    f"{self.budget.researcher_attempts} 次尝试。请使用已有 findings "
                    "继续后续流程。"
                ),
                tool_call_id=tool_call_id,
            )

        if self.evidence_inventory is not None:
            plan_result = self.evidence_inventory.evaluate_research_plan()
            if not plan_result.passed:
                return self._researcher_rejection(
                    message=plan_result.message,
                    tool_call_id=tool_call_id,
                )

        # With no configured reserve, retain the original generic behavior.
        if reserved == 0 or calls < initial_limit:
            self.budget.researcher_calls += 1
            return None

        self.budget.researcher_recovery_attempts += 1
        description = str(args.get("description") or "")
        if self.evidence_inventory is None:
            return self._researcher_rejection(
                message=(
                    "委派被拒绝：恢复 researcher 需要启用 evidence inventory。"
                ),
                tool_call_id=tool_call_id,
                recovery_attempt=True,
            )

        if self.evidence_inventory.inspection_calls == 0:
            return self._researcher_rejection(
                message=(
                    "委派被拒绝：最后一个 researcher 名额专门保留给证据恢复。"
                    "请先调用 check_evidence_inventory，确认仍有 citation_deficit 后再使用。"
                ),
                tool_call_id=tool_call_id,
                recovery_attempt=True,
            )

        evidence = self.evidence_inventory.snapshot()
        if evidence.passed:
            return self._researcher_rejection(
                message=(
                    "委派被拒绝：证据清单已经达到最少来源数量，"
                    "无需消耗保留的恢复 researcher；请继续分析或起草。"
                ),
                tool_call_id=tool_call_id,
                recovery_attempt=True,
            )

        if RECOVERY_MARKER not in description:
            return self._researcher_rejection(
                message=(
                    "委派被拒绝：最后一个 researcher 名额只能用于证据恢复。"
                    f"description 必须以 {RECOVERY_MARKER} 标记，并说明当前缺口、"
                    "已有 eligible URLs、不同的新来源目标和新的 findings 精确路径。"
                ),
                tool_call_id=tool_call_id,
                recovery_attempt=True,
            )

        filenames = TASK_FINDINGS_PATH_RE.findall(description)
        if not filenames:
            return self._researcher_rejection(
                message=(
                    "委派被拒绝：证据恢复任务必须包含新的精确路径 "
                    "/workspace/sources/findings_<slug>.md。"
                ),
                tool_call_id=tool_call_id,
                recovery_attempt=True,
            )
        existing = {
            path.name for path in self.evidence_inventory._evidence_paths()
        }
        if all(filename in existing for filename in filenames):
            return self._researcher_rejection(
                message=(
                    "委派被拒绝：证据恢复必须写入新的 findings 文件，"
                    "禁止覆盖已有 findings。"
                ),
                tool_call_id=tool_call_id,
                recovery_attempt=True,
            )

        self.budget.researcher_calls += 1
        self.budget.researcher_recovery_calls += 1
        if self.search_budget is not None:
            self.search_budget.recovery_active = True
        return None

    def _normalize_task_request(
        self, request: ToolCallRequest
    ) -> tuple[ToolCallRequest, ToolMessage | None]:
        """Repair a common nested task-argument shape before schema validation."""

        tool_call = request.tool_call or {}
        if tool_call.get("name") != "task":
            return request, None

        args = dict(tool_call.get("args") or {})
        nested = args.pop("parameters", None)
        if isinstance(nested, dict):
            for key in ("description", "subagent_type"):
                if not args.get(key) and nested.get(key):
                    args[key] = nested[key]

        subagent_type = str(
            args.get("subagent_type") or args.get("subagent") or ""
        )
        description = str(args.get("description") or "").strip()
        normalized_call = {**tool_call, "args": args}
        if hasattr(request, "override"):
            normalized_request = request.override(tool_call=normalized_call)
        else:
            request.tool_call = normalized_call
            normalized_request = request

        if description:
            return normalized_request, None

        counter_prefix = subagent_type if subagent_type in {
            "researcher",
            "analyst",
            "editor",
        } else None
        if counter_prefix:
            attempts_name = f"{counter_prefix}_attempts"
            rejections_name = f"{counter_prefix}_rejections"
            setattr(
                self.budget,
                attempts_name,
                int(getattr(self.budget, attempts_name, 0)) + 1,
            )
            setattr(
                self.budget,
                rejections_name,
                int(getattr(self.budget, rejections_name, 0)) + 1,
            )
        return normalized_request, ToolMessage(
            content=(
                "委派被拒绝：task 缺少非空 description。"
                "该无效调用未消耗子 Agent 执行名额；请使用顶层 "
                "description 与 subagent_type 参数重新委派。"
            ),
            tool_call_id=tool_call.get("id") or "",
            name="task",
            status="error",
        )
    
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
            if self._is_draft_file(file_path):
                evidence_rejection = self._evidence_gate_or_reject(
                    stage="draft_creation" if name == "write_file" else "draft_revision",
                    tool_call_id=tool_call_id,
                    tool_name=name,
                )
                if evidence_rejection is not None:
                    return evidence_rejection
            if name == "write_file" and self._is_report_file(file_path):
                evidence_rejection = self._evidence_gate_or_reject(
                    stage="final_report",
                    tool_call_id=tool_call_id,
                    tool_name=name,
                    output_text=self._extract_file_content(args),
                    enforce_output_citations=True,
                )
                if evidence_rejection is not None:
                    return evidence_rejection
            if name == "edit_file" and self._is_draft_file(file_path):
                return self._count_or_reject(
                    counter_name="draft_edit_calls",
                    limit_name="max_draft_edits",
                    label="draft edit_file",
                    tool_call_id=tool_call_id,
                    tool_name=name,
                    guidance="请一次性完成草稿修订，然后写入 final report。",
                )
            return None
        if name == "task":
            subagent_type = args.get("subagent_type") or args.get("subagent") or ""

            if subagent_type == "analyst":
                evidence_rejection = self._evidence_gate_or_reject(
                    stage="analyst_delegation",
                    tool_call_id=tool_call_id,
                    tool_name="task",
                )
                if evidence_rejection is not None:
                    return evidence_rejection

            if subagent_type == "researcher" and (
                self.evidence_inventory is not None
                or int(getattr(self.budget, "reserved_researcher_calls", 0)) > 0
            ):
                return self._researcher_or_reject(
                    args=args,
                    tool_call_id=tool_call_id,
                )

            task_limits = {
                "researcher": (
                    "researcher_calls",
                    "max_researcher",
                    "请使用已有 findings 继续后续流程。",
                ),
                "analyst": (
                    "analyst_calls",
                    "max_analyst",
                    "请基于已有 analysis 继续起草 draft，不要再次委派 analyst。",
                ),
                "editor": (
                    "editor_calls",
                    "max_editor",
                    "请根据已有审阅意见修订 draft，并立刻写入 final report。",
                ),
            }
            if subagent_type in task_limits:
                counter_name, limit_name, guidance = task_limits[subagent_type]
                return self._count_or_reject(
                    counter_name=counter_name,
                    limit_name=limit_name,
                    label=subagent_type,
                    tool_call_id=tool_call_id,
                    tool_name="task",
                    guidance=guidance,
                )
        
        return None

    def wrap_tool_call(
        self, 
        request: ToolCallRequest,
        handler: Callable[[ToolCallRequest], Any]
    ) -> Any:

        request, malformed = self._normalize_task_request(request)
        if malformed is not None:
            return malformed
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
        request, malformed = self._normalize_task_request(request)
        if malformed is not None:
            return malformed
        rejected = self._check_or_reject(request)
        if rejected is not None:
            print(f"[guard] blocked task subagent={ (request.tool_call or {}).get('args', {}).get('subagent_type') }")
            return rejected
        
        return await handler(request)



