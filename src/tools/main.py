import asyncio
import sys
import argparse
import json
import time

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

async def measure_stage(stage_name: str, coro) -> dict:
    start = time.perf_counter()

    try: 
        result = await coro
        cost_ms = int((time.perf_counter() - start) * 1000)

        return {
            "stage": stage_name,
            "ok": True,
            "cost_ms": cost_ms,
            "result": result,
            "error": None,
        }
    except Exception as e:
        cost_ms = int((time.perf_counter() - start) * 1000)
        return {
            "stage": stage_name,
            "ok": False,
            "cost_ms": cost_ms,
            "result": None,
            "error": str(e),
        }

async def run_pipeline_with_metrics(topic: str, no_analysis: bool) -> dict:

    total_start = time.perf_counter()

    pipeline_report = await measure_stage(
        "pipeline",
        run_pipeline(topic=topic, no_analysis=no_analysis),
    )

    total_ms = int((time.perf_counter() - total_start) * 1000)

    return {
        "ok": pipeline_report["ok"],
        "total_ms": total_ms,
        "stages": [pipeline_report],
        "data": pipeline_report["result"],
        "error": pipeline_report["error"],
    }

def print_metrics(metrics: dict):
    status = "✅ 成功" if metrics["ok"] else "❌ 失败"
    print(f"\n[Metrics] {status} | total={metrics['total_ms']} ms")

    for s in metrics["stages"]:
        mark = "OK" if s["ok"] else "ERR"
        print(f"  - {s['stage']}: {mark}, {s['cost_ms']} ms")

        if s["error"]:
            print(f"    error: {s['error']}")


async def main():
    args = parse_args()
    topic = args.topic.strip()
    if not topic:
        raise ValueError("topic 不能为空")

    # out = await run_researcher_once("AI Agent 框架对比")
    # topic = parse_topic_from_argv()
    # out = await run_workflow(topic)
    # out = await run_pipeline(topic=topic, no_analysis=args.no_analysis)
    metrics = await run_pipeline_with_metrics(topic=topic, no_analysis=args.no_analysis)
    if not metrics["ok"]:
        print_metrics(metrics)
        raise RuntimeError(metrics["error"] or "pipeline 执行失败")

    out = metrics["data"]

    if args.as_json:
        output = {"result": out, "metrics": metrics}
        print(json.dumps(output, ensure_ascii=False, indent=2))
    else:
        print(out["final_text"])
        print_metrics(metrics)

if __name__ == "__main__":
    asyncio.run(main())