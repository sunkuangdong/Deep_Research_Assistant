from __future__ import annotations

import argparse
import asyncio
import json
import os
import re
import shutil
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

from evals.langfuse_observability import (
    flush_langfuse,
    start_case_trace,
    validate_langfuse_config,
)
from evals.runtime_config import capture_runtime_config
from evals.scoring import score_workspace
from evals.validation import load_jsonl, validate_dataset
from src.workflow.deepagents_runner import run_deepagents_workflow

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _safe_name(value: str) -> str:
    return re.sub(r"[^a-zA-Z0-9_.-]+", "_", value).strip("_") or "unknown"


def _redact_error(exc: BaseException) -> str:
    text = f"{type(exc).__name__}: {exc}"
    for name in (
        "OPENAI_API_KEY",
        "BOCHA_API_KEY",
        "LANGFUSE_PUBLIC_KEY",
        "LANGFUSE_SECRET_KEY",
    ):
        secret = os.getenv(name)
        if secret:
            text = text.replace(secret, "[REDACTED]")
    return text[:2000]


def _prepare_run_root(run_root: Path) -> None:
    if run_root.exists():
        shutil.rmtree(run_root)
    (run_root / "workspace/sources").mkdir(parents=True)
    (run_root / "workspace/reports").mkdir(parents=True)
    shutil.copy2(PROJECT_ROOT / "AGENTS.md", run_root / "AGENTS.md")
    shutil.copytree(PROJECT_ROOT / "skills", run_root / "skills")


def _enhanced_topic(case: dict[str, Any]) -> str:
    headings = ", ".join(case["required_sections"])
    if case["language"] == "zh":
        return (
            f"{case['topic']}\n\n"
            f"评估输出要求：最终报告必须使用以下完全一致的 Markdown 二级标题：{headings}；"
            f"最终报告至少包含 {case['minimum_citations']} 个不同的 HTTP(S) 来源链接。"
        )
    return (
        f"{case['topic']}\n\n"
        "Evaluation output requirement: the final report must use these exact Markdown "
        f"level-two headings: {headings}; include at least {case['minimum_citations']} "
        "distinct HTTP(S) source links in the final report."
    )


def _append_jsonl(path: Path, payload: dict[str, Any]) -> None:
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, ensure_ascii=False) + "\n")


async def _run_case(
    case: dict[str, Any],
    result_dir: Path,
    timeout_seconds: int,
    *,
    trace_metadata: dict[str, Any] | None = None,
    trace_session_id: str | None = None,
) -> dict[str, Any]:
    case_root = result_dir / "workspaces" / case["id"]
    _prepare_run_root(case_root)
    started_at = datetime.now(UTC)
    start = time.perf_counter()
    base_result: dict[str, Any] = {
        "case_id": case["id"],
        "started_at": started_at.isoformat(),
        "status": "infrastructure_failure",
        "failure_type": None,
        "error": None,
    }
    with start_case_trace(
        case=case,
        session_id=trace_session_id or result_dir.name,
        metadata=trace_metadata or {},
    ) as case_trace:
        if case_trace.trace_id:
            base_result["langfuse_trace_id"] = case_trace.trace_id
        try:
            workflow_result = await asyncio.wait_for(
                run_deepagents_workflow(
                    _enhanced_topic(case),
                    no_analysis=case["no_analysis"],
                    root_dir=case_root,
                    todos_export_path=case_root / "tmp.json",
                    callbacks=case_trace.callbacks,
                ),
                timeout=timeout_seconds,
            )
            score = score_workspace(
                case_root / "workspace", case, workflow_result.metadata
            )
            base_result.update(
                {
                    "status": "completed" if score["completed"] else "agent_failure",
                    "failure_type": (
                        None if score["completed"] else "acceptance_criteria"
                    ),
                    "final_text": workflow_result.final_text,
                    "metadata": workflow_result.metadata,
                    "score": score,
                }
            )
        except TimeoutError as exc:
            base_result.update(
                {
                    "failure_type": "timeout",
                    "error": _redact_error(exc),
                }
            )
        except Exception as exc:  # noqa: BLE001 - failures must become benchmark data
            base_result.update(
                {
                    "failure_type": "provider_or_runtime",
                    "error": _redact_error(exc),
                }
            )
        base_result["latency_ms"] = int((time.perf_counter() - start) * 1000)
        base_result["finished_at"] = datetime.now(UTC).isoformat()
        case_trace.record_result(base_result)
        if case_trace.error:
            base_result["langfuse_error"] = case_trace.error
    return base_result


def _write_summary(result_dir: Path, results: list[dict[str, Any]]) -> None:
    completed = sum(result["status"] == "completed" for result in results)
    summary = {
        "run_count": len(results),
        "completed_count": completed,
        "completion_rate": completed / len(results) if results else 0,
        "status_counts": {
            status: sum(result["status"] == status for result in results)
            for status in ("completed", "agent_failure", "infrastructure_failure")
        },
        "note": "Cost and aggregate token/latency statistics are phase 6 and are not finalized here.",
    }
    (result_dir / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    config = json.loads((result_dir / "config.json").read_text(encoding="utf-8"))
    rows = []
    for result in results:
        usage = (result.get("metadata") or {}).get("usage") or {}
        score = result.get("score") or {}
        rows.append(
            "| {case_id} | {status} | {latency_ms} | {tokens} | {citations} |".format(
                case_id=result["case_id"],
                status=result["status"],
                latency_ms=result["latency_ms"],
                tokens=usage.get("total_tokens", "n/a"),
                citations=score.get("citation_count", "n/a"),
            )
        )
    report = "\n".join(
        [
            "# Deep Research Evaluation Run",
            "",
            f"- Model: `{config['model_name']}`",
            f"- Dataset SHA-256: `{config['dataset_sha256']}`",
            f"- Completed: {completed}/{len(results)}",
            "",
            "| Case | Status | Latency (ms) | Total tokens | Citations |",
            "| --- | --- | ---: | ---: | ---: |",
            *rows,
            "",
            "Cost and aggregate token/latency statistics are intentionally deferred to phase 6.",
            "",
        ]
    )
    (result_dir / "report.md").write_text(report, encoding="utf-8")


async def async_main(args: argparse.Namespace) -> int:
    load_dotenv(PROJECT_ROOT / ".env")
    validate_langfuse_config()
    dataset_path = (PROJECT_ROOT / args.dataset).resolve()
    validation = validate_dataset(dataset_path)
    if validation["errors"]:
        raise ValueError("dataset validation failed: " + "; ".join(validation["errors"]))

    cases = load_jsonl(dataset_path)
    if args.case_id:
        requested = set(args.case_id)
        cases = [case for case in cases if case["id"] in requested]
        found = {case["id"] for case in cases}
        if found != requested:
            raise ValueError(f"unknown case ids: {sorted(requested - found)}")

    timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    model = _safe_name(os.getenv("MODEL_NAME") or "gpt-6-luna")
    dataset_name = _safe_name(dataset_path.stem)
    result_dir = (
        Path(args.result_dir).resolve()
        if args.result_dir
        else PROJECT_ROOT / "evals/results" / f"{timestamp}_{model}_{dataset_name}"
    )
    result_dir.mkdir(parents=True, exist_ok=False)

    config = capture_runtime_config(PROJECT_ROOT, dataset_path, args.timeout_seconds)
    config["selected_case_ids"] = [case["id"] for case in cases]
    config["run_type"] = "smoke" if "smoke" in dataset_path.stem else "main"
    (result_dir / "config.json").write_text(
        json.dumps(config, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    trace_metadata = {
        key: config[key]
        for key in (
            "protocol_version",
            "dataset_version",
            "dataset_sha256",
            "git_commit",
            "provider",
            "model_name",
            "run_type",
        )
    }
    results: list[dict[str, Any]] = []
    raw_path = result_dir / "raw_runs.jsonl"
    try:
        for case in cases:
            print(f"[eval] running {case['id']} (timeout={args.timeout_seconds}s)")
            result = await _run_case(
                case,
                result_dir,
                args.timeout_seconds,
                trace_metadata=trace_metadata,
                trace_session_id=result_dir.name,
            )
            _append_jsonl(raw_path, result)
            results.append(result)
            print(
                f"[eval] {case['id']}: {result['status']} "
                f"({result['latency_ms']} ms)"
            )

        _write_summary(result_dir, results)
    finally:
        flush_langfuse()
    print(f"[eval] results: {result_dir}")
    return 0 if all(result["status"] == "completed" for result in results) else 2


def main() -> int:
    parser = argparse.ArgumentParser(description="Run Deep Research benchmark cases")
    parser.add_argument(
        "--dataset",
        default="evals/datasets/research_smoke_v1.jsonl",
        help="Dataset path relative to the project root",
    )
    parser.add_argument("--case-id", action="append", help="Run only this case; repeatable")
    parser.add_argument("--timeout-seconds", type=int, default=900)
    parser.add_argument("--result-dir")
    args = parser.parse_args()
    if args.timeout_seconds <= 0:
        parser.error("--timeout-seconds must be positive")
    return asyncio.run(async_main(args))


if __name__ == "__main__":
    raise SystemExit(main())
