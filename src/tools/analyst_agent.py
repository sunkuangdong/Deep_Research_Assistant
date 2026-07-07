from src.tools.lib.model import get_model
from langchain.agents import create_agent

from src.tools.agent import run_researcher_once
from src.tools.agent import review_with_editor
from src.tools.lib.prompts import ANALYST_SYSTEM_PROMPT

def create_analyst_agent():
    model = get_model()
    analyst_agent = create_agent(
        model=model,
        tools=[],
        system_prompt=ANALYST_SYSTEM_PROMPT,
    )
    return analyst_agent

async def analyze_with_analyst(research_text: str) -> str:
    text = (research_text or "").strip()

    if not text:
        raise ValueError("research_text 不能为空")

    agent = create_analyst_agent()

    result = await agent.ainvoke(
        {
            "messages": [
                {
                    "role": "user",
                    "content": (
                        "请对以下调研内容做结构化分析，输出：\n"
                        "1) 关键维度对比\n"
                        "2) 结论与建议\n"
                        "3) 仍不确定的信息\n\n"
                        f"{text}"
                    ),
                }
            ]
        }
    )
    messages = result.get("messages", [])

    if not messages:
        raise RuntimeError("没有获取到结果")

    return messages[-1].content

def should_run_analysis(subtopic: str) -> bool:
    topic = (subtopic or "").lower()
    keywords = ["对比", "比较", "排名", "优劣", "趋势", "增长", "占比", "分析"]
    return any(k in topic for k in keywords)

async def run_research_analyze_review(subtopic: str) -> str:
    research_output = await run_researcher_once(subtopic)
    if should_run_analysis(subtopic):
        analysis_output = await analyze_with_analyst(research_output)

        draft_for_editor = (
            "=== 调研结果 ===\n"
            f"{research_output}\n\n"
            "=== 分析结果 ===\n"
            f"{analysis_output}"
        )
    else:
        analysis_output = "（该主题无需额外数据分析）"
        draft_for_editor = (
            "=== 调研结果 ===\n"
            f"{research_output}"
        )
    
    review_output = await review_with_editor(draft_for_editor)

    return (
        "=== 调研结果 ===\n"
        f"{research_output}\n\n"
        "=== 分析结果 ===\n"
        f"{analysis_output}\n\n"
        "=== 编辑审阅意见 ===\n"
        f"{review_output}"
    )

