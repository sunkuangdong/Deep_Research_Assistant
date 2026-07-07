import asyncio
# from src.tools.analyst_agent import run_research_analyze_review
from src.tools.editor import run_workflow

async def main():
    # out = await run_researcher_once("AI Agent 框架对比")
    out = await run_workflow("AI Agent 框架对比")
    print(out)

if __name__ == "__main__":
    asyncio.run(main())