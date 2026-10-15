from __future__ import annotations

import hashlib
import os
import subprocess
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

from evals.langfuse_observability import langfuse_tracing_enabled


def sanitize_base_url(raw_url: str | None) -> str:
    value = (raw_url or "https://api.openai.com/v1").strip()
    parsed = urlsplit(value)
    hostname = parsed.hostname or ""
    port = f":{parsed.port}" if parsed.port else ""
    return urlunsplit((parsed.scheme or "https", f"{hostname}{port}", parsed.path, "", ""))


def infer_provider(base_url: str) -> str:
    host = (urlsplit(base_url).hostname or "").lower()
    if host == "api.openai.com" or host.endswith(".openai.com"):
        return "openai"
    if "dashscope" in host or host.endswith("aliyuncs.com"):
        return "dashscope"
    return "openai-compatible"


def git_commit(project_root: Path) -> str:
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=project_root,
        check=False,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip() if result.returncode == 0 else "unknown"


def dataset_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def capture_runtime_config(
    project_root: Path,
    dataset_path: Path,
    timeout_seconds: int,
) -> dict[str, object]:
    base_url = sanitize_base_url(os.getenv("OPENAI_BASE_URL"))
    return {
        "protocol_version": "1.0.0-draft",
        "dataset_version": "v1",
        "dataset_path": str(dataset_path.relative_to(project_root)),
        "dataset_sha256": dataset_sha256(dataset_path),
        "git_commit": git_commit(project_root),
        "provider": infer_provider(base_url),
        "model_name": (os.getenv("MODEL_NAME") or "gpt-6-luna").strip(),
        "model_base_url": base_url,
        "model_max_input_tokens": int(os.getenv("MODEL_MAX_INPUT_TOKENS") or "131072"),
        "reasoning_effort": (os.getenv("MODEL_REASONING_EFFORT") or "none").strip(),
        "temperature": 0,
        "timeout_seconds": timeout_seconds,
        "max_provider_retries": int(os.getenv("MODEL_MAX_RETRIES") or "2"),
        "concurrency": 1,
        "search_call_limit": 6,
        "analyst_call_limit": 1,
        "editor_call_limit": 1,
        "langfuse_tracing_enabled": langfuse_tracing_enabled(),
        "langfuse_environment": (
            os.getenv("LANGFUSE_TRACING_ENVIRONMENT") or "default"
        ).strip(),
        "langfuse_base_url": sanitize_base_url(
            os.getenv("LANGFUSE_BASE_URL") or "https://cloud.langfuse.com"
        ),
    }
