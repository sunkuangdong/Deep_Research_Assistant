from __future__ import annotations
from src.tools.deepagents_adapter import (
    build_deep_agent,
    run_deep_agent_once,
    DeepAgentBuildConfig,
)
from src.tools.lib.prompts import (
    ORCHESTRATOR_SYSTEM_PROMPT,
    RUNTIME_DELEGATION_GUARD,
    RUNTIME_NO_ANALYSIS_GUARD,
)

def build_deepagents_system_prompt(no_analysis: bool = False) -> str:
    """
    构建 DeepAgents 主 Agent 的 system_prompt。
    注意：
        - ORCHESTRATOR_SYSTEM_PROMPT 是主 Agent 的长期角色设定
        - RUNTIME_DELEGATION_GUARD 是委派约束
        - RUNTIME_NO_ANALYSIS_GUARD 是本次运行的 no_analysis 约束
    """

    sections = [
        ORCHESTRATOR_SYSTEM_PROMPT.strip(),
        RUNTIME_DELEGATION_GUARD.strip(),
    ]

    if no_analysis:
        sections.append(RUNTIME_NO_ANALYSIS_GUARD.strip())

    return "\n\n".join(sections)


async def run_deepagents_workflow(
    topic: str,
    no_analysis: bool = False,
    enabled_skills: list[str] = [],
) -> str:
    """
    运行官方 DeepAgents 工作流。
    第 4 步只建立业务编排入口。
    第 5 步会在这里接入 deepagents_adapter。
    第 6 步职责：
        1) 接收 main.py 传来的 topic / skills / no_analysis
        2) 构建 system_prompt
        3) 构建官方 DeepAgent
        4) 执行一次 agent.ainvoke
        5) 返回最终文本
    """

    clean_topic = (topic or "").strip()

    system_prompt = build_deepagents_system_prompt(no_analysis=no_analysis)

    config = DeepAgentBuildConfig(
        root_dir=".",
        skills=["./skills"],
        memory=["./AGENTS.md"],
        system_prompt=system_prompt,
        debug=False,
        name="deep_research_agent",
    )

    agent = build_deep_agent(config)

    user_prompt = (
        f"请围绕这个主题完成调研并给出最终报告：{clean_topic}\n\n"
        "要求：所有输出使用中文。"
    )

    if enabled_skills:
        user_prompt += (
            "\n\n当前 CLI 请求启用的 skills："
            f"{', '.join(enabled_skills)}。\n"
            "注意：官方 SkillsMiddleware 会在第 7 步接入 skills/ 目录后正式生效。"
        )
    
    return await run_deep_agent_once(agent, user_prompt)


