from pyexpat.errors import messages
from langchain.agents import create_agent
from src.tools.lib.model import get_model
from src.tools.lib.prompts import ORCHESTRATOR_SYSTEM_PROMPT
from src.tools.subagent_tools import task_researcher, task_analyst, task_editor


def create_orchestrator_agent():
    model = get_model()
    orchestrator = create_agent(
        model=model,
        system_prompt=ORCHESTRATOR_SYSTEM_PROMPT,
        tools=[task_researcher, task_analyst, task_editor],
    )
    return orchestrator

async def run_orchestrator_once(topic: str) -> str:
    clean_topic = (topic or "").strip()

    if not clean_topic:
        raise ValueError("topic 不能为空")
    
    agent = create_orchestrator_agent()

    result = await agent.invoke({
        "messages": [
            {
                "role": "user",
                "content": f"请围绕这个主题完成调研并给出最终报告：{clean_topic}",
            }
        ]
    })

    messages = result.get("messages", [])

    if not messages:
        raise RuntimeError("orchestrator 没有返回结果")
    
    return messages[-1].get("content", "")