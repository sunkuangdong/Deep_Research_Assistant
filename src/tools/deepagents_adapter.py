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

def build_deep_agent(config: DeepAgentBuildConfig) -> Any:
    """
    创建官方 DeepAgent。
    当前职责：
        1) 创建 FilesystemBackend
        2) 获取项目统一模型
        3) 调用 create_deep_agent
        4) 返回可 ainvoke 的 agent graph
    """

    backend = FilesystemBackend(root_dir=config.root_dir)
    model = get_model()

    agent = create_deep_agent(
        model=model,
        backend=backend,
        name=config.name,
        skills=config.skills or [],
        memory=config.memory or [],
        system_prompt=config.system_prompt,
        debug=config.debug,
    )
    return agent

async def run_deep_agent_once(agent: Any, topic: str) -> str:
    """
    执行一次 DeepAgent 调用，并提取最终文本。
    """

    cleaned_topic = (topic or "").strip()

    if not cleaned_topic:
        raise ValueError("topic 不能为空")

    result = await agent.ainvoke({
        "messages": [
            {"role": "user", "content": cleaned_topic}
        ]
    })

    messages = result.get("messages", [])

    if not messages:
        raise ValueError("deep agent 没有返回 messages")

    return messages[-1].content







