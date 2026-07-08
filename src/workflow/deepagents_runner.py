from __future__ import annotations

async def run_deepagents_workflow(
    topic: str,
    no_analysis: bool = False,
    enabled_skills: list[str] = [],
) -> str:
    """
        运行官方 DeepAgents 工作流。
        当前第 4 步只建立业务编排入口。
        第 5 步会在这里接入 deepagents_adapter。
    """

    cleaned_topic = (topic or "").strip()

    if not cleaned_topic:
        raise ValueError("topic 不能为空")

    skills = enabled_skills or []

    return (
        "deepagents runner 已接入入口，但尚未创建官方 create_deep_agent。\n"
        f"topic: {cleaned_topic}\n"
        f"enabled_skills: {skills}\n"
        f"no_analysis: {no_analysis}"
    )


