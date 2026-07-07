from langchain.agents import create_agent
from src.tools.lib.model import get_model
from src.tools.lib.prompts import ORCHESTRATOR_SYSTEM_PROMPT, RUNTIME_NO_ANALYSIS_GUARD, RUNTIME_DELEGATION_GUARD
from src.tools.subagent_tools import task_researcher, task_analyst, task_editor


def create_orchestrator_agent():
    model = get_model()
    orchestrator = create_agent(
        model=model,
        system_prompt=ORCHESTRATOR_SYSTEM_PROMPT,
        tools=[task_researcher, task_analyst, task_editor],
    )
    return orchestrator

async def run_orchestrator_once(topic: str, no_analysis: bool = False) -> str:
    clean_topic = (topic or "").strip()
    runtime_guard = ""
    runtime_sections = [RUNTIME_DELEGATION_GUARD.strip()]

    if not clean_topic:
        raise ValueError("topic 不能为空")

    agent = create_orchestrator_agent()

    if no_analysis:
        runtime_sections.append(RUNTIME_NO_ANALYSIS_GUARD.strip())
        runtime_guard = "\n\n".join(runtime_sections)

    user_prompt = (
        f"请围绕这个主题完成调研并给出最终报告：{clean_topic}\n\n"
        f"{runtime_guard}"
    )

    result = await agent.ainvoke(
        {
            "messages": [
                {"role": "user", "content": user_prompt}
            ]
        }
    )

    messages = result.get("messages", [])

    if not messages:
        raise RuntimeError("orchestrator 没有返回结果")
    
    return messages[-1].content