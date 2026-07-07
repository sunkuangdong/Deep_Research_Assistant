import asyncio
import json

from src.workflow.cli import parse_args
from src.workflow.engine import run_staged_workflow
from src.workflow.metrics import print_stage_metrics
from src.workflow.runtime import healthcheck_env, print_quick_tips_on_error


async def main():
    args = parse_args()
    topic = args.topic.strip()
    if not topic:
        raise ValueError("topic 不能为空")

    report = await run_staged_workflow(topic=topic, no_analysis=args.no_analysis)
    if not report["ok"]:
        print_stage_metrics(report)
        raise RuntimeError(report["error"] or "流程执行失败")

    result = report["result"]
    if args.as_json:
        print(json.dumps({"result": result, "metrics": report}, ensure_ascii=False, indent=2))
    else:
        print(result["final_text"])
        print_stage_metrics(report)


if __name__ == "__main__":
    try:
        healthcheck_env()
        asyncio.run(main())
    except Exception as e:
        print(f"❌ 执行失败: {e}")
        print_quick_tips_on_error(e)
        raise SystemExit(1)
