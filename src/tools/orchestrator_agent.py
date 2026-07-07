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

async def run_orchestrator_once(topic: str, no_analysis: bool = False) -> str:
    clean_topic = (topic or "").strip()
    runtime_guard = ""

    if not clean_topic:
        raise ValueError("topic 不能为空")

    agent = create_orchestrator_agent()

    if no_analysis:
        runtime_guard = (
            "\n\n[运行时约束]\n"
            "- 本次任务禁止调用分析师（task_analyst）。\n"
            "- 只允许调研与审阅流程。\n"
            "- 如遇到需要数值分析的内容，请在结论中明确说明“本次按 no-analysis 跳过分析步骤”。"
        )

    result = await agent.ainvoke(
        {
            "messages": [
                {
                    "role": "user",
                    "content": (
                        f"请围绕这个主题完成调研并给出最终报告：{clean_topic}"
                        f"{runtime_guard}"
                    ),
                }
            ]
        }
    )

    messages = result.get("messages", [])

    if not messages:
        raise RuntimeError("orchestrator 没有返回结果")
    
    return messages[-1].content