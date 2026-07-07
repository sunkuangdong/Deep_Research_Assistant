import asyncio
import sys
import argparse
import json

# from src.tools.analyst_agent import run_research_analyze_review
from src.tools.editor import run_workflow
from src.tools.agent import run_research_then_review

def parse_topic_from_argv() -> str:
    if len(sys.argv) < 2:
        raise ValueError("请提供一个主题")
    topic = " ".join(sys.argv[1:]).strip()

    if not topic:
        raise ValueError("主题不能为空")
    
    return topic

def parse_args() -> dict:
    parser = argparse.ArgumentParser(description="Deep Research Assistant CLI")
    parser.add_argument("topic", type=str, help="调研主题，例如：AI Agent 框架对比")
    parser.add_argument(
        "--json",
        action="store_true",
        help="输出 JSON 格式",
        dest="as_json",
    )
    parser.add_argument(
        "--no-analysis",
        action="store_true",
        help="跳过分析步骤，只做调研+审阅",
    )

    return parser.parse_args()

async def run_pipeline(topic: str, no_analysis: bool) -> dict:
    if no_analysis:
        text = await run_research_then_review(topic)
        return {
            "topic": topic,
            "research": text,
            "analysis": "（已通过 --no-analysis 跳过）",
            "review": "",
            "final_text": text,
        }
    else:
        return await run_workflow(topic)

async def main():
    args = parse_args()
    topic = args.topic.strip()
    if not topic:
        raise ValueError("topic 不能为空")

    # out = await run_researcher_once("AI Agent 框架对比")
    # topic = parse_topic_from_argv()
    # out = await run_workflow(topic)
    out = await run_pipeline(topic=topic, no_analysis=args.no_analysis)
    if args.as_json:
        print(json.dumps(out, ensure_ascii=False, indent=2))
    else:
        print(out["final_text"])

if __name__ == "__main__":
    asyncio.run(main())