from src.tools.agent import run_researcher_once, review_with_editor
from src.tools.analyst_agent import should_run_analysis, analyze_with_analyst

def build_editor_input(research_output: str, analysis_output: str) -> str:
    if analysis_output:
        return (
            "=== 调研结果 ===\n"
            f"{research_output}\n\n"
            "=== 分析结果 ===\n"
            f"{analysis_output}"
        )
    return (
        "=== 调研结果 ===\n"
        f"{research_output}"
    )

def format_workflow_output(
    topic: str,
    research_output: str,
    analysis_output: str,
    review_output: str,
) -> dict:
    return {
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

async def run_workflow(topic: str) -> dict:
    clean_topic = (topic or "").strip()

    if not clean_topic:
        raise ValueError("topic 不能为空")
    
    research_output = await run_researcher_once(clean_topic)

    # 是否需要进行数据分析
    if should_run_analysis(clean_topic):
        analysis_output = await analyze_with_analyst(research_output)
    else:
        analysis_output = "（该主题无需额外数据分析）"

    # 审阅
    draft_for_editor = build_editor_input(
        research_output=research_output,
        analysis_output=None if analysis_output.startswith("（该主题无需") else analysis_output,
    )

    review_output = await review_with_editor(draft_for_editor)

    # output
    return format_workflow_output(
        topic=clean_topic,
        research_output=research_output,
        analysis_output=analysis_output,
        review_output=review_output,
    )
    

    





