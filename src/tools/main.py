import asyncio
from .agent import run_research_then_review

async def main():
    out = await run_research_then_review("AI Agent 框架对比")
    print(out)

if __name__ == "__main__":
    asyncio.run(main())