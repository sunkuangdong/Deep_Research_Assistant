import asyncio
import json

from src.workflow.cli import parse_args
from src.workflow.runtime import healthcheck_env, print_quick_tips_on_error
from src.tools.orchestrator_agent import run_orchestrator_once


async def main():
    args = parse_args()
    topic = args.topic.strip()
    if not topic:
        raise ValueError("topic 不能为空")
    final_text = await run_orchestrator_once(topic, no_analysis=args.no_analysis)
    if args.as_json:
        print(
            json.dumps(
                {
                    "topic": topic,
                    "final_text": final_text,
                    "mode": "subagent-orchestrator",
                },
                ensure_ascii=False,
                indent=2,
            )
        )
    else:
        print(final_text)


if __name__ == "__main__":
    try:
        healthcheck_env()
        asyncio.run(main())
    except Exception as e:
        print(f"❌ 执行失败: {e}")
        print_quick_tips_on_error(e)
        raise SystemExit(1)
