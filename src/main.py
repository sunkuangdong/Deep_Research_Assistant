import asyncio
import json
import time

from src.workflow.cli import parse_args, parse_skills_arg
from src.workflow.runtime import healthcheck_env, print_quick_tips_on_error
from src.tools.orchestrator_agent import run_orchestrator_once
from src.workflow.metrics import get_tool_metrics_summary, reset_tool_metrics
from src.workflow.skills import resolve_enabled_skills
from src.workflow.deepagents_runner import run_deepagents_workflow


async def main():
    args = parse_args()
    print("args:", args)
    topic = args.topic.strip()
    requested_skills = parse_skills_arg(args.skills)
    enabled_skills = resolve_enabled_skills(requested_skills, use_defaults=True)

    if not topic:
        raise ValueError("topic 不能为空")
    
    reset_tool_metrics()
    start_time = time.perf_counter()

    if args.mode == "legacy":
        final_text = await run_orchestrator_once(
            topic,
            no_analysis=args.no_analysis,
            enabled_skills=enabled_skills,
        )
    elif args.mode == "deepagents":
        final_text = await run_deepagents_workflow(
            topic,
            enabled_skills=enabled_skills,
            no_analysis=args.no_analysis,
        )
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
        }
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(final_text)
        print(f"\n[Total] {total_ms} ms")
        print(json.dumps(tool_metrics, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    try:
        healthcheck_env()
        asyncio.run(main())
    except Exception as e:
        print(f"❌ 执行失败: {e}")
        print_quick_tips_on_error(e)
        raise SystemExit(1)
