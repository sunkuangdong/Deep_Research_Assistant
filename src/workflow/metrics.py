from operator import truediv
import time
from functools import wraps
from collections import defaultdict

TOOL_METRICS = {
    "counts": defaultdict(int),
    "durations_ms": defaultdict(list),
}

def timed_tool(tool_name: str):
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            start = time.perf_counter()
            try:
                return await func(*args, **kwargs)
            finally:
                elapsed_ms = int((time.perf_counter() - start) * 1000)
                TOOL_METRICS["counts"][tool_name] += 1
                TOOL_METRICS["durations_ms"][tool_name].append(elapsed_ms)
                print(f"⏱️ {tool_name} 耗时: {elapsed_ms} ms")
        return wrapper
    return decorator

def get_tool_metrics_summary() -> dict:
    summary = {}
    for name, count in TOOL_METRICS["counts"].items():
        durations = TOOL_METRICS["durations_ms"][name]
        total = sum(durations)
        avg = int(total / count) if count else 0
        summary[name] = {
            "count": count,
            "total_ms": total,
            "avg_ms": avg,
            "max_ms": max(durations) if durations else 0,
            "min_ms": min(durations) if durations else 0,
        }
    return summary

def reset_tool_metrics():
    TOOL_METRICS["counts"].clear()
    TOOL_METRICS["durations_ms"].clear()

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


def print_stage_metrics(report: dict):
    status = "✅ 成功" if report.get("ok") else "❌ 失败"
    print(f"\n[Metrics] {status} | total={report.get('total_ms', 0)} ms")

    for stage in report.get("stages", []):
        mark = "OK" if stage.get("ok") else "ERR"
        stage_name = stage.get("stage", "unknown")
        cost = stage.get("cost_ms", 0)

        if stage.get("result") == "SKIPPED":
            print(f"  - {stage_name}: SKIPPED")
        else:
            print(f"  - {stage_name}: {mark}, {cost} ms")

        if stage.get("error"):
            print(f"    error: {stage['error']}")
