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
    return parser.parse_args()
