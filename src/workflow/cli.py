import argparse


def parse_args():
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
    parser.add_argument(
        "--skills",
        type=str,
        default="",
        help="启用的 skills，逗号分隔，例如：web-research,report-writer",
    )
    parser.add_argument(
        "--mode",
        type=str,
        choices=["legacy", "deepagents"],
        default="legacy",
        help="运行模式：legacy=现有 LangChain agent 流程，deepagents=官方 create_deep_agent 流程"
    )
    return parser.parse_args()

def parse_skills_arg(skills_arg: str) -> list[str]:
    raw = (skills_arg or "").strip()

    if not raw:
        return []
    
    return [s.strip() for s in raw.split(",") if s.strip()]