import time

from src.tools.agent import run_researcher_once, review_with_editor
from src.tools.analyst_agent import analyze_with_analyst, should_run_analysis
from src.workflow.metrics import measure_stage


# async def run_pipeline(topic: str, no_analysis: bool) -> dict:
#     if no_analysis:
#         text = await run_research_then_review(topic)
#         return {
#             "topic": topic,
#             "research": text,
#             "analysis": "（已通过 --no-analysis 跳过）",
#             "review": "",
#             "final_text": text,
#         }
#     return await run_workflow(topic)


# async def run_pipeline_with_metrics(topic: str, no_analysis: bool) -> dict:
#     total_start = time.perf_counter()
#     pipeline_report = await measure_stage(
#         "pipeline",
#         run_pipeline(topic=topic, no_analysis=no_analysis),
#     )
#     total_ms = int((time.perf_counter() - total_start) * 1000)
#     return {
#         "ok": pipeline_report["ok"],
#         "total_ms": total_ms,
#         "stages": [pipeline_report],
#         "data": pipeline_report["result"],
#         "error": pipeline_report["error"],
#     }


async def run_research_phase(clean_topic: str) -> dict:
    return await measure_stage("research", run_researcher_once(clean_topic))


async def run_analysis_phase(research_output: str, no_analysis: bool) -> tuple[dict, str, str]:
    analysis_output = "（该主题无需额外数据分析）"
    need_analysis = (not no_analysis) and should_run_analysis(research_output)

    if need_analysis:
        analysis_stage = await measure_stage(
            "analysis",
            analyze_with_analyst(research_output),
        )
        if not analysis_stage["ok"]:
            return analysis_stage, analysis_output, ""

        analysis_output = analysis_stage["result"]
        draft_for_editor = (
            "=== 调研结果 ===\n"
            f"{research_output}\n\n"
            "=== 分析结果 ===\n"
            f"{analysis_output}"
        )
        return analysis_stage, analysis_output, draft_for_editor

    analysis_stage = {
        "stage": "analysis",
        "ok": True,
        "cost_ms": 0,
        "result": "SKIPPED",
        "error": None,
    }
    draft_for_editor = "=== 调研结果 ===\n" f"{research_output}"
    return analysis_stage, analysis_output, draft_for_editor


async def run_review_phase(draft_for_editor: str) -> dict:
    return await measure_stage("review", review_with_editor(draft_for_editor))


def _error_report(topic: str, stages: list[dict], error: str, total_start: float) -> dict:
    return {
        "ok": False,
        "topic": topic,
        "stages": stages,
        "error": error,
        "total_ms": int((time.perf_counter() - total_start) * 1000),
        "result": None,
    }


def _append_stage_or_error(
    topic: str,
    stages: list[dict],
    stage: dict,
    total_start: float,
) -> dict | None:
    stages.append(stage)
    if not stage.get("ok"):
        return _error_report(topic, stages, stage.get("error", "未知错误"), total_start)
    return None


def _success_report(
    topic: str,
    stages: list[dict],
    research_output: str,
    analysis_output: str,
    review_output: str,
    total_start: float,
) -> dict:
    result = {
        "topic": topic,
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
        "topic": topic,
        "stages": stages,
        "total_ms": int((time.perf_counter() - total_start) * 1000),
        "error": None,
        "result": result,
    }


async def run_staged_workflow(topic: str, no_analysis: bool = False) -> dict:
    clean_topic = (topic or "").strip()
    if not clean_topic:
        raise ValueError("topic 不能为空")

    total_start = time.perf_counter()
    stages = []

    # 1
    research_stage = await run_research_phase(clean_topic)
    failure = _append_stage_or_error(clean_topic, stages, research_stage, total_start)
    if failure:
        return failure
    research_output = research_stage["result"]

    # 2
    analysis_stage, analysis_output, draft_for_editor = await run_analysis_phase(
        research_output,
        no_analysis,
    )
    failure = _append_stage_or_error(clean_topic, stages, analysis_stage, total_start)
    if failure:
        return failure

    # 3
    review_stage = await run_review_phase(draft_for_editor)
    failure = _append_stage_or_error(clean_topic, stages, review_stage, total_start)
    if failure:
        return failure
    review_output = review_stage["result"]

    return _success_report(
        clean_topic,
        stages,
        research_output,
        analysis_output,
        review_output,
        total_start,
    )
