from langchain_core.tools import tool
from pydantic import BaseModel, Field

from src.tools.agent import run_researcher_once, review_with_editor
from src.tools.analyst_agent import analyze_with_analyst
from src.workflow.metrics import timed_tool

class ResearchTaskInput(BaseModel):
    subtopic: str = Field(..., min_length=1, description="要调研的子主题（中文）")

class AnalysisTaskInput(BaseModel):
    research_text: str = Field(..., min_length=1, description="调研员产出的调研文本")

class EditorTaskInput(BaseModel):
    draft: str = Field(..., min_length=1, description="待审阅的草稿内容")

@tool("task_researcher", args_schema=ResearchTaskInput)
@timed_tool("task_researcher")
async def task_researcher(subtopic: str) -> str:
     """委派调研员：调研一个子主题并返回结果。"""
     print("📊 调用 task_researcher")
     return await run_researcher_once(subtopic)

@tool("task_analyst", args_schema=AnalysisTaskInput)
@timed_tool("task_analyst")
async def task_analyst(research_text: str) -> str:
    """委派分析师：对调研文本做结构化分析。"""
    print("📊 调用 task_analyst")
    return await analyze_with_analyst(research_text)

@tool("task_editor", args_schema=EditorTaskInput)
@timed_tool("task_editor")
async def task_editor(draft: str) -> str:
    """委派编辑：审阅草稿并返回审阅意见。"""
    print("📝 调用 task_editor")
    return await review_with_editor(draft)
