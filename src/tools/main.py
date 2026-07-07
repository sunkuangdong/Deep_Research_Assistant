import asyncio
from src.tools.analyst_agent import run_research_analyze_review

async def main():
    out = await run_research_analyze_review("AI Agent 框架对比")
    print(out)

if __name__ == "__main__":
    asyncio.run(main())