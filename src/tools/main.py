import asyncio
import sys
# from src.tools.analyst_agent import run_research_analyze_review
from src.tools.editor import run_workflow

def parse_topic_from_argv() -> str:
    if len(sys.argv) < 2:
        raise ValueError("请提供一个主题")
    topic = " ".join(sys.argv[1:]).strip()

    if not topic:
        raise ValueError("主题不能为空")
    
    return topic


async def main():
    topic = parse_topic_from_argv()
    # out = await run_researcher_once("AI Agent 框架对比")
    out = await run_workflow(topic)
    print(out)

if __name__ == "__main__":
    asyncio.run(main())