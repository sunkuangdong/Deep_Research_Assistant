from langchain.agents import create_agent

from .search import web_search
from .lib.model import get_model


RESEARCHER_SYSTEM_PROMPT = """
    你是一名专业调研员，只负责一个子主题调研，所有输出必须中文。
    工作要求：
    1) 最多调用 3 次 web_search；
    2) 给出结构化结论：关键发现 + 证据来源 URL；
    3) 禁止空转循环，拿到足够信息后立即给出结论；
    4) 不要偏离用户给定的子主题。
"""

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

if __name__ == "__main__":
    import asyncio
    async def main():
        out = await run_researcher_once("AI Agent 框架对比")
        print(out)
    asyncio.run(main())




