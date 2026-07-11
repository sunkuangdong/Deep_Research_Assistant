import os
from langchain_openai import ChatOpenAI

def get_model() -> ChatOpenAI:
    api_key = (os.getenv("OPENAI_API_KEY") or "").strip()
    if not api_key:
        raise ValueError("未设置 OPENAI_API_KEY")
    model_name = (os.getenv("MODEL_NAME") or "gpt-4o").strip()
    base_url = (os.getenv("OPENAI_BASE_URL") or "").strip() or None

    llm_kwargs = {
        "model": model_name,
        "temperature": 0,
        "api_key": api_key,
    }
    if base_url:
        llm_kwargs["base_url"] = base_url

    model = ChatOpenAI(**llm_kwargs)

    return model