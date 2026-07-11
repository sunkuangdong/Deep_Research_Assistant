from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from deepagents import create_deep_agent
from deepagents.backends.filesystem import FilesystemBackend

from src.tools.lib.model import get_model

@dataclass(frozen=True)
class DeepAgentBuildConfig:
    """
        构建官方 DeepAgent 所需的配置。
        先把 create_deep_agent 的核心参数收拢到一个对象里，
        后面 runner 只需要传配置，不直接关心官方 API 细节。
    """

    root_dir: str = '.'
    skills: list[str] | None = None
    memory: list[str] | None = None
    system_prompt: str | None = None
    debug: bool = False
    name: str = "deep_research_agent"
    virtual_mode: bool = True
    tools: list[Any] | None = None
    subagents: list[Any] | None = None

def build_deep_agent(config: DeepAgentBuildConfig) -> Any:
    """
    创建官方 DeepAgent。
    当前职责：
        1) 创建 FilesystemBackend
        2) 获取项目统一模型
        3) 调用 create_deep_agent
        4) 返回可 ainvoke 的 agent graph
    """

    backend = FilesystemBackend(root_dir=config.root_dir, virtual_mode=config.virtual_mode)
    model = get_model()

    agent = create_deep_agent(
        model=model,
        tools=config.tools or [],
        backend=backend,
        name=config.name,
        skills=config.skills or [],
        memory=config.memory or [],
        system_prompt=config.system_prompt,
        debug=config.debug,
        subagents=config.subagents or [],
    )
    return agent


def _get_message_content(message: Any) -> str:
    if hasattr(message, "content"):
        return str(message.content)

    if isinstance(message, dict):
        return str(message.get("content") or "")

    return str(message or "")


def _extract_final_text(output: Any) -> str | None:
    if isinstance(output, dict):
        messages = output.get("messages")
        if messages:
            return _get_message_content(messages[-1])

    return None


def _summarize_tool_input(name: str, data: dict[str, Any]) -> str:
    tool_input = (data or {}).get("input")
    if not isinstance(tool_input, dict):
        return ""

    if name == "web_search":
        query = tool_input.get("query")
        count = tool_input.get("count")
        if query:
            count_text = f", count={count}" if count is not None else ""
            return f" query={query!r}{count_text}"

    if name == "task":
        description = tool_input.get("description") or tool_input.get("task")
        subagent_type = tool_input.get("subagent_type")
        parts: list[str] = []
        if subagent_type:
            parts.append(f"subagent={subagent_type}")
        if description:
            parts.append(f"task={str(description)[:80]!r}")
        if parts:
            return " " + ", ".join(parts)

    if name in {"write_file", "edit_file", "read_file"}:
        file_path = tool_input.get("file_path") or tool_input.get("path")
        if file_path:
            return f" path={file_path!r}"

    return ""


def _format_deepagents_event(event: dict[str, Any]) -> str | None:
    event_type = event.get("event", "")
    name = event.get("name", "")
    data = event.get("data") or {}

    if event_type in {"on_chat_model_start", "on_llm_start"}:
        return f"[event] model_start: {name}"

    if event_type in {"on_chat_model_end", "on_llm_end"}:
        return f"[event] model_end: {name}"

    if event_type == "on_tool_start":
        detail = _summarize_tool_input(name, data)
        return f"[event] tool_start: {name}{detail}"

    if event_type == "on_tool_end":
        return f"[event] tool_end: {name}"

    return None


async def run_deep_agent_once(agent: Any, topic: str) -> str:
    """
    执行一次 DeepAgent 调用，默认打印 streaming events，并提取最终文本。
    """

    cleaned_topic = (topic or "").strip()

    if not cleaned_topic:
        raise ValueError("topic 不能为空")

    final_text = None

    async for event in agent.astream_events(
        {
            "messages": [
                {"role": "user", "content": cleaned_topic}
            ]
        },
        config={"recursion_limit": 50},
        version="v2",
    ):
        formatted = _format_deepagents_event(event)
        if formatted:
            print(formatted)

        if event.get("event") == "on_chain_end":
            extracted = _extract_final_text((event.get("data") or {}).get("output"))
            if extracted:
                final_text = extracted

    if not final_text:
        raise ValueError("deep agent 没有返回 messages")

    return final_text







