import asyncio
import json
import time

from src.workflow.cli import parse_args
from src.workflow.runtime import healthcheck_env, print_quick_tips_on_error
from src.workflow.metrics import get_tool_metrics_summary, reset_tool_metrics
from src.workflow.deepagents_runner import run_deepagents_workflow

from dotenv import load_dotenv
load_dotenv()


async def main():
    args = parse_args()
    topic = args.topic.strip()

    if not topic:
        raise ValueError("topic 不能为空")
    
    reset_tool_metrics()
    start_time = time.perf_counter()
    deepagents_metadata = {}

    if args.mode == "deepagents":
        deepagents_result = await run_deepagents_workflow(
            topic,
            no_analysis=args.no_analysis,
        )
        final_text = deepagents_result.final_text
        deepagents_metadata = deepagents_result.metadata
    else:
        raise ValueError(f"不支持的运行模式: {args.mode}")

    
    total_ms = int((time.perf_counter() - start_time) * 1000)
    tool_metrics = get_tool_metrics_summary()
    
    if args.as_json:
        payload = {
            "topic": topic,
            "final_text": final_text,
            "mode": args.mode,
            "total_ms": total_ms,
            "tool_metrics": tool_metrics,
            "deepagents": deepagents_metadata,
            "no_analysis": args.no_analysis,
        }
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(final_text)
        print(f"\n[Total] {total_ms} ms")
        if deepagents_metadata:
            print("\n[DeepAgents Metadata]")
            print(json.dumps(deepagents_metadata, ensure_ascii=False, indent=2))
        print(json.dumps(tool_metrics, ensure_ascii=False, indent=2))



if __name__ == "__main__":
    try:
        healthcheck_env()
        asyncio.run(main())
    except Exception as e:
        print(f"❌ 执行失败: {e}")
        print_quick_tips_on_error(e)
        raise SystemExit(1)
