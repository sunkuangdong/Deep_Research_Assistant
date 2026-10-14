import os
from langchain_openai import ChatOpenAI
from langchain_core.language_models import ModelProfile


_SUPPORTED_REASONING_EFFORTS = {
    "none",
    "minimal",
    "low",
    "medium",
    "high",
    "xhigh",
    "max",
}


def _resolve_reasoning_effort(model_name: str) -> str | None:
    configured = (os.getenv("MODEL_REASONING_EFFORT") or "").strip().lower()
    if not configured and model_name.lower() == "gpt-6-luna":
        configured = "none"

    if configured and configured not in _SUPPORTED_REASONING_EFFORTS:
        supported = ", ".join(sorted(_SUPPORTED_REASONING_EFFORTS))
        raise ValueError(
            f"MODEL_REASONING_EFFORT={configured!r} is invalid; "
            f"expected one of: {supported}"
        )

    return configured or None


def get_model() -> ChatOpenAI:
    api_key = (os.getenv("OPENAI_API_KEY") or "").strip()
    if not api_key:
        raise ValueError("未设置 OPENAI_API_KEY")

    model_name = (os.getenv("MODEL_NAME") or "gpt-6-luna").strip()
    base_url = (os.getenv("OPENAI_BASE_URL") or "").strip() or None
    reasoning_effort = _resolve_reasoning_effort(model_name)

    max_input_tokens = int((os.getenv("MODEL_MAX_INPUT_TOKENS") or "131072").strip())

    llm_kwargs = {
        "model": model_name,
        "temperature": 0,
        "api_key": api_key,
        # 流式调用时也返回 token 用量（astream_events 场景下统计成本需要）
        "stream_usage": True,
    }
    if base_url:
        llm_kwargs["base_url"] = base_url
    if reasoning_effort:
        # GPT-6 Luna tool calling through Chat Completions requires `none`.
        llm_kwargs["reasoning_effort"] = reasoning_effort

    model = ChatOpenAI(**llm_kwargs)

    profile: ModelProfile = dict(model.profile or {})
    profile["max_input_tokens"] = max_input_tokens

    return model.model_copy(update={"profile": profile})
