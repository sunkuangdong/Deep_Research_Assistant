from __future__ import annotations

import os
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Any

TRUE_VALUES = {"1", "true", "yes", "on"}
FALSE_VALUES = {"", "0", "false", "no", "off"}


def langfuse_tracing_enabled() -> bool:
    raw_value = (os.getenv("LANGFUSE_TRACING_ENABLED") or "").strip().lower()
    if raw_value in TRUE_VALUES:
        return True
    if raw_value in FALSE_VALUES:
        return False
    raise ValueError(
        "LANGFUSE_TRACING_ENABLED must be one of: true, false, 1, 0, yes, no, on, off"
    )


def validate_langfuse_config() -> bool:
    """Validate tracing before a paid model call can start."""

    if not langfuse_tracing_enabled():
        return False

    required = (
        "LANGFUSE_PUBLIC_KEY",
        "LANGFUSE_SECRET_KEY",
        "LANGFUSE_BASE_URL",
    )
    missing = [name for name in required if not (os.getenv(name) or "").strip()]
    if missing:
        raise ValueError(
            "Langfuse tracing is enabled but these variables are missing: "
            + ", ".join(missing)
        )
    _load_langfuse_dependencies()
    return True


def _load_langfuse_dependencies() -> tuple[Any, Any, Any]:
    try:
        from langfuse import get_client, propagate_attributes
        from langfuse.langchain import CallbackHandler
    except ImportError as exc:
        raise RuntimeError(
            "Langfuse tracing is enabled but the langfuse package is not installed. "
            "Run: python -m pip install -r requirements-dev.txt"
        ) from exc
    return get_client, propagate_attributes, CallbackHandler


@dataclass
class CaseTrace:
    callbacks: list[Any] = field(default_factory=list)
    trace_id: str | None = None
    span: Any | None = None
    error: str | None = None

    @property
    def enabled(self) -> bool:
        return self.span is not None

    def record_result(self, result: dict[str, Any]) -> None:
        """Attach local deterministic results without changing benchmark status."""

        if self.span is None:
            return

        try:
            metadata = result.get("metadata") or {}
            score = result.get("score") or {}
            self.span.update(
                output={
                    "status": result.get("status"),
                    "failure_type": result.get("failure_type"),
                    "latency_ms": result.get("latency_ms"),
                    "usage": metadata.get("usage") or {},
                    "score": score,
                }
            )
            self.span.score_trace(
                name="completed",
                value=1 if result.get("status") == "completed" else 0,
                data_type="BOOLEAN",
            )

            if not score:
                return

            self.span.score_trace(
                name="artifact_completeness",
                value=float(score.get("artifact_completeness") or 0),
                data_type="NUMERIC",
            )
            self.span.score_trace(
                name="citation_count",
                value=float(score.get("citation_count") or 0),
                data_type="NUMERIC",
            )
            if "language_compliance" in score:
                self.span.score_trace(
                    name="language_compliance",
                    value=1 if score.get("language_compliance") else 0,
                    data_type="BOOLEAN",
                )
            if score.get("report_date_compliance") is not None:
                self.span.score_trace(
                    name="report_date_compliance",
                    value=1 if score.get("report_date_compliance") else 0,
                    data_type="BOOLEAN",
                )
            for check_name, passed in (score.get("source_link_checks") or {}).items():
                self.span.score_trace(
                    name=f"source_{check_name}",
                    value=1 if passed else 0,
                    data_type="BOOLEAN",
                )
            for budget_name, passed in (score.get("budget_checks") or {}).items():
                self.span.score_trace(
                    name=f"{budget_name}_budget_compliance",
                    value=1 if passed else 0,
                    data_type="BOOLEAN",
                )
        except Exception as exc:  # noqa: BLE001 - telemetry must not change eval status
            self.error = type(exc).__name__


@contextmanager
def start_case_trace(
    *,
    case: dict[str, Any],
    session_id: str,
    metadata: dict[str, Any],
) -> Iterator[CaseTrace]:
    if not validate_langfuse_config():
        yield CaseTrace()
        return

    get_client, propagate_attributes, callback_handler_class = (
        _load_langfuse_dependencies()
    )
    langfuse = get_client()
    trace_input = {
        "case_id": case["id"],
        "topic": case["topic"],
        "language": case["language"],
        "no_analysis": case["no_analysis"],
    }
    tags = [
        "deep-research-evaluation",
        str(metadata.get("run_type") or "unknown"),
        str(metadata.get("dataset_version") or "unknown"),
    ]

    with langfuse.start_as_current_observation(
        as_type="span",
        name="deep-research-eval-case",
        input=trace_input,
    ) as span, propagate_attributes(
        trace_name="deep-research-eval-case",
        session_id=session_id,
        tags=tags,
        metadata=metadata,
        version=str(metadata.get("git_commit") or "unknown"),
    ):
        handler = callback_handler_class()
        yield CaseTrace(
            callbacks=[handler],
            trace_id=span.trace_id,
            span=span,
        )


def flush_langfuse() -> None:
    if not langfuse_tracing_enabled():
        return
    get_client, _, _ = _load_langfuse_dependencies()
    get_client().flush()
