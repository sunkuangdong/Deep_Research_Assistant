import asyncio
import sys
import argparse
import json
import time

# from src.tools.analyst_agent import run_research_analyze_review
from src.tools.editor import run_workflow
from src.tools.agent import run_research_then_review
from src.tools.agent import run_researcher_once, review_with_editor
from src.tools.analyst_agent import analyze_with_analyst, should_run_analysis


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

async def run_staged_workflow(topic: str, no_analysis: bool = False) -> dict:
    clean_topic = (topic or "").strip()

    if not clean_topic:
        raise ValueError("topic 不能为空")

    total_start = time.perf_counter()
    stages = []

    research_stage = await measure_stage(
        "research",
        run_researcher_once(clean_topic),
    )

    stages.append(research_stage)

    if not research_stage["ok"]:
        return {
            "ok": False,
            "topic": clean_topic,
            "stages": stages,
            "error": research_stage["error"],
            "total_ms": int((time.perf_counter() - total_start) * 1000),
            "result": None,
        }
    
    research_output = research_stage["result"]

    analysis_output = "(该主题无需额外数据分析)"

    need_analysis = (not no_analysis) and should_run_analysis(research_output)

    if need_analysis:
        analysis_stage = await measure_stage(
            "analysis",
            analyze_with_analyst(research_output),
        )
        stages.append(analysis_stage)

        if not analysis_stage["ok"]:
            return {
                "ok": False,
                "topic": clean_topic,
                "stages": stages,
                "error": analysis_stage["error"],
                "total_ms": int((time.perf_counter() - total_start) * 1000),
                "result": None,
            }

        analysis_output = analysis_stage["result"]
        draft_for_editor = (
            "=== 调研结果 ===\n"
            f"{research_output}\n\n"
            "=== 分析结果 ===\n"
            f"{analysis_output}"
        )
    else:
        stages.append(
            {
                "stage": "analysis",
                "ok": True,
                "cost_ms": 0,
                "result": "SKIPPED",
                "error": None,
            }
        )
        draft_for_editor = (
            "=== 调研结果 ===\n"
            f"{research_output}"
        )

    review_stage = await measure_stage(
        "review",
        review_with_editor(draft_for_editor),
    )

    stages.append(review_stage)
    if not review_stage["ok"]:
        return {
            "ok": False,
            "topic": clean_topic,
            "stages": stages,
            "total_ms": int((time.perf_counter() - total_start) * 1000),
            "error": review_stage["error"],
            "result": None,
        }
    review_output = review_stage["result"]
    result = {
        "topic": clean_topic,
        "research": research_output,
        "analysis": analysis_output,
        "review": review_output,
        "final_text": (
            "=== 调研结果 ===\n"
            f"{research_output}\n\n"
            "=== 分析结果 ===\n"
            f"{analysis_output}\n\n"
            "=== 编辑审阅意见 ===\n"
            f"{review_output}"
        ),
    }

    return {
        "ok": True,
        "topic": clean_topic,
        "stages": stages,
        "total_ms": int((time.perf_counter() - total_start) * 1000),
        "error": None,
        "result": result,
    }

def print_stage_metrics(report: dict):
    status = "✅ 成功" if report.get("ok") else "❌ 失败"
    print(f"\n[Metrics] {status} | total={report.get('total_ms', 0)} ms")

    for s in report.get("stages", []):
        mark = "OK" if s.get("ok") else "ERR"
        stage = s.get("stage", "unknown")
        cost = s.get("cost_ms", 0)
        if s.get("result") == "SKIPPED":
            print(f"  - {stage}: SKIPPED")
        else:
            print(f"  - {stage}: {mark}, {cost} ms")
        if s.get("error"):
            print(f"    error: {s['error']}")

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
    asyncio.run(main())