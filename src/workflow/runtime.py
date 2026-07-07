import os

def healthcheck_env():
    required = ["OPENAI_API_KEY", "BOCHA_API_KEY"]

    missing = [env for env in required if not (os.getenv(env) or "").strip()]

    if missing:
        raise ValueError(f"缺少以下环境变量: {', '.join(missing)}")

    print("环境变量检查通过")

def print_quick_tips_on_error(err: Exception):
    msg = str(err)

    print("\n[排障建议]")
    if "OPENAI_API_KEY" in msg:
        print("- 在 .env 配置 OPENAI_API_KEY")
    elif "BOCHA_API_KEY" in msg:
        print("- 在 .env 配置 BOCHA_API_KEY，并确认账号有额度")
    elif "ModuleNotFoundError" in msg or "ImportError" in msg:
        print("- 使用模块方式运行：python -m src.main \"你的主题\"")
    else:
        print("- 先激活虚拟环境：source .venv/bin/activate")
        print("- 再看 Metrics 哪个阶段失败（research/analysis/review）")
