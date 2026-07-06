from langchain.agents import create_agent

from .search import web_search
from .lib.model import get_model
from .lib.prompts import RESEARCHER_SYSTEM_PROMPT   
from .lib.prompts import EDITOR_SYSTEM_PROMPT


def create_researcher_agent():
    model = get_model()

    researcher_agent = create_agent(
        model=model,
        tools=[web_search],
        system_prompt=RESEARCHER_SYSTEM_PROMPT,
    )

    return researcher_agent

async def run_researcher_once(subtopic: str) -> str:
    topic = (subtopic or "").strip()

    if not topic:
        raise ValueError("subtopic 不能为空")
    
    agent = create_researcher_agent()

    result = await agent.ainvoke(
        {
            "messages": [
                {
                    "role": "user",
                    "content": f"请调研这个子主题：{topic}，并给出来源 URL"
                }
            ]
        }
    )

    messages = result.get("messages", [])
    if not messages:
        raise RuntimeError("没有获取到结果")
    
    return messages[-1].content

def create_editor_agent():
    model = get_model()
    editor_agent = create_agent(
        model=model,
        tools=[],
        system_prompt=EDITOR_SYSTEM_PROMPT,
    )
    return editor_agent

async def review_with_editor(draft: str) -> str:
    text = (draft or "").strip()

    if not text:
        raise ValueError("draft 不能为空")

    agent = create_editor_agent()

    result = await agent.ainvoke(
        {
            "messages": [
                {
                    "role": "user",
                    "content": (
                        "请审阅以下调研草稿，并给出中文审阅意见与可执行修改建议：\n\n"
                        f"{text}"
                    ),
                }
            ]
        }
    )

    messages = result.get("messages", [])

    if not messages:
        raise RuntimeError("没有获取到结果")
    
    return messages[-1].content

async def run_research_then_review(subtopic: str) -> str:
    research_output = await run_researcher_once(subtopic)
    review_output = await review_with_editor(research_output)
    return (
        "=== 调研结果 ===\n"
        f"{research_output}\n\n"
        "=== 编辑审阅意见 ===\n"
        f"{review_output}"
    )


