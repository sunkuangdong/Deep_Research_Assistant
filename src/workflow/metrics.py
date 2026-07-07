import time


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
