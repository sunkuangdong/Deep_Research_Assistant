from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import statistics
from collections import Counter
from copy import deepcopy
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from evals.scoring import score_workspace
from evals.validation import load_jsonl, validate_dataset

PROJECT_ROOT = Path(__file__).resolve().parents[1]
CALL_FIELDS = (
    "search_calls",
    "fetch_calls",
    "researcher_calls",
    "analyst_calls",
    "editor_calls",
    "draft_edit_calls",
)
STABILITY_COMPATIBILITY_KEYS = (
    "protocol_version",
    "dataset_version",
    "dataset_sha256",
    "provider",
    "model_name",
    "model_base_url",
    "model_max_input_tokens",
    "reasoning_effort",
    "temperature",
    "timeout_seconds",
    "max_provider_retries",
    "concurrency",
    "deepagents_recursion_limit",
    "search_call_limit",
    "search_recovery_reserve",
    "search_timeout_seconds",
    "search_max_retries",
    "fetch_call_limit",
    "fetch_recovery_reserve",
    "fetch_timeout_seconds",
    "fetch_max_retries",
    "fetch_max_bytes",
    "fetch_max_chars",
    "researcher_call_limit",
    "researcher_initial_call_limit",
    "researcher_recovery_call_limit",
    "analyst_call_limit",
    "editor_call_limit",
    "draft_edit_call_limit",
    "evidence_inventory_gate",
    "structured_research_plan_gate",
    "langfuse_tracing_enabled",
    "langfuse_environment",
    "langfuse_base_url",
    "run_date",
)


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def _write_json(path: Path, payload: Any) -> None:
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.write_text(
        "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows),
        encoding="utf-8",
    )


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _display_path(path: Path) -> str:
    try:
        return path.relative_to(PROJECT_ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def _round(value: float | None, places: int = 6) -> float | None:
    if value is None:
        return None
    return round(float(value), places)


def _numeric_stats(values: list[int | float], *, expected_count: int) -> dict[str, Any]:
    if not values:
        return {
            "sample_count": 0,
            "missing_count": expected_count,
            "minimum": None,
            "maximum": None,
            "range": None,
            "mean": None,
            "median": None,
            "sample_stddev": None,
            "coefficient_of_variation": None,
        }
    numbers = [float(value) for value in values]
    mean = statistics.fmean(numbers)
    stddev = statistics.stdev(numbers) if len(numbers) >= 2 else None
    return {
        "sample_count": len(numbers),
        "missing_count": expected_count - len(numbers),
        "minimum": _round(min(numbers)),
        "maximum": _round(max(numbers)),
        "range": _round(max(numbers) - min(numbers)),
        "mean": _round(mean),
        "median": _round(statistics.median(numbers)),
        "sample_stddev": _round(stddev),
        "coefficient_of_variation": (
            _round(stddev / mean) if stddev is not None and mean else None
        ),
    }


def validate_stability_subset(dataset_path: Path, subset_path: Path) -> dict[str, Any]:
    validation = validate_dataset(dataset_path)
    if validation["errors"]:
        raise ValueError(
            "dataset validation failed: " + "; ".join(validation["errors"])
        )
    subset = _read_json(subset_path)
    if subset.get("status") != "FROZEN":
        raise ValueError("stability subset must have FROZEN status")
    dataset_digest = _sha256(dataset_path)
    if subset.get("source_dataset_sha256") != dataset_digest:
        raise ValueError("stability subset dataset SHA-256 does not match")

    cases = load_jsonl(dataset_path)
    case_by_id = {str(case["id"]): case for case in cases}
    case_ids = [str(case_id) for case_id in subset.get("case_ids") or []]
    if len(case_ids) != 10 or len(set(case_ids)) != 10:
        raise ValueError("stability subset must contain ten unique case IDs")
    unknown = sorted(set(case_ids) - set(case_by_id))
    if unknown:
        raise ValueError(f"stability subset contains unknown case IDs: {unknown}")

    selected = [case_by_id[case_id] for case_id in case_ids]
    actual_strata = {
        "languages": dict(
            sorted(Counter(case["language"] for case in selected).items())
        ),
        "categories": dict(
            sorted(Counter(case["category"] for case in selected).items())
        ),
        "analysis_requirement": {
            "analysis": sum(not bool(case["no_analysis"]) for case in selected),
            "no_analysis": sum(bool(case["no_analysis"]) for case in selected),
        },
    }
    if actual_strata != subset.get("strata"):
        raise ValueError("stability subset strata do not match selected cases")
    repeat_plan = subset.get("repeat_plan") or {}
    if repeat_plan != {
        "total_runs_per_case": 3,
        "reused_main_v2_runs_per_case": 1,
        "additional_runs_per_case": 2,
        "task_count": 10,
        "total_observations": 30,
        "additional_paid_runs": 20,
    }:
        raise ValueError("stability subset repeat plan is invalid")
    if (subset.get("selection_policy") or {}).get("uses_outcome_fields") is not False:
        raise ValueError("stability selection policy must exclude outcome fields")
    return {
        "valid": True,
        "dataset_sha256": dataset_digest,
        "subset_sha256": _sha256(subset_path),
        "case_ids": case_ids,
        "strata": actual_strata,
        "repeat_plan": repeat_plan,
        "subset": subset,
        "case_by_id": case_by_id,
    }


def _load_main_bundle(
    main_bundle_dir: Path,
    subset_validation: dict[str, Any],
) -> tuple[dict[str, Any], list[dict[str, Any]], dict[str, dict[str, Any]]]:
    config_path = main_bundle_dir / "config.json"
    runs_path = main_bundle_dir / "rescored_runs.jsonl"
    if not config_path.is_file() or not runs_path.is_file():
        raise FileNotFoundError(
            "main bundle is missing config.json or rescored_runs.jsonl"
        )
    config = _read_json(config_path)
    if config.get("dataset_sha256") != subset_validation["dataset_sha256"]:
        raise ValueError("main bundle dataset SHA-256 does not match the subset")
    if config.get("protocol_version") != subset_validation["subset"].get(
        "source_protocol_version"
    ):
        raise ValueError("main bundle protocol does not match the subset")
    runs = _read_jsonl(runs_path)
    by_id = {str(run["case_id"]): run for run in runs}
    missing = sorted(set(subset_validation["case_ids"]) - set(by_id))
    if missing:
        raise ValueError(f"main bundle is missing stability cases: {missing}")

    results_root = main_bundle_dir.parent.parent
    source_configs: dict[str, dict[str, Any]] = {}
    for case_id in subset_validation["case_ids"]:
        source_dir = str(by_id[case_id].get("source_result_dir") or "")
        source_path = results_root / source_dir / "config.json"
        if not source_path.is_file():
            raise FileNotFoundError(
                f"main source config is unavailable for {case_id}: {source_path}"
            )
        source_configs[case_id] = _read_json(source_path)
    return config, runs, source_configs


def _compatibility_value(config: dict[str, Any], key: str) -> str:
    return json.dumps(config.get(key), ensure_ascii=False, sort_keys=True)


def _validate_compatible_configs(
    baseline: dict[str, Any],
    candidates: list[tuple[str, dict[str, Any]]],
) -> None:
    for label, candidate in candidates:
        mismatches = [
            key
            for key in STABILITY_COMPATIBILITY_KEYS
            if _compatibility_value(candidate, key)
            != _compatibility_value(baseline, key)
        ]
        if mismatches:
            raise ValueError(
                f"{label} is incompatible with the main run: {', '.join(mismatches)}"
            )


def validate_stability_preflight(
    dataset_path: Path,
    subset_path: Path,
    main_bundle_dir: Path,
) -> dict[str, Any]:
    subset_validation = validate_stability_subset(dataset_path, subset_path)
    main_config, main_runs, main_source_configs = _load_main_bundle(
        main_bundle_dir, subset_validation
    )
    case_ids = subset_validation["case_ids"]
    baseline_config = main_source_configs[case_ids[0]]
    _validate_compatible_configs(
        baseline_config,
        [
            (f"main source {case_id}", main_source_configs[case_id])
            for case_id in case_ids[1:]
        ],
    )
    main_by_id = {str(run["case_id"]): run for run in main_runs}
    trace_ids = [
        str(main_by_id[case_id].get("langfuse_trace_id") or "") for case_id in case_ids
    ]
    if any(not trace_id for trace_id in trace_ids) or len(set(trace_ids)) != len(
        trace_ids
    ):
        raise ValueError("main stability observations require unique trace IDs")
    statuses = Counter(str(main_by_id[case_id]["status"]) for case_id in case_ids)
    return {
        "valid": True,
        "dataset_sha256": subset_validation["dataset_sha256"],
        "subset_sha256": subset_validation["subset_sha256"],
        "case_ids": case_ids,
        "strata": subset_validation["strata"],
        "main_observation_status_counts": dict(sorted(statuses.items())),
        "protocol_version": main_config["protocol_version"],
        "model_name": main_config["model_name"],
        "run_date": baseline_config["run_date"],
        "main_source_git_commits": sorted(
            {
                str(config.get("git_commit") or "unknown")
                for config in main_source_configs.values()
            }
        ),
    }


def _load_repeat_dir(
    repeat_dir: Path,
    expected_case_ids: list[str],
) -> tuple[dict[str, Any], dict[str, dict[str, Any]]]:
    config_path = repeat_dir / "config.json"
    raw_path = repeat_dir / "raw_runs.jsonl"
    if not config_path.is_file() or not raw_path.is_file():
        raise FileNotFoundError(
            f"repeat directory is missing config.json or raw_runs.jsonl: {repeat_dir}"
        )
    config = _read_json(config_path)
    configured_ids = [str(case_id) for case_id in config.get("selected_case_ids") or []]
    if configured_ids != expected_case_ids:
        raise ValueError(
            f"repeat directory {repeat_dir.name} does not use the frozen case order"
        )
    raw_rows = _read_jsonl(raw_path)
    raw_ids = [str(row.get("case_id") or "") for row in raw_rows]
    if raw_ids != expected_case_ids or len(set(raw_ids)) != len(raw_ids):
        raise ValueError(
            f"repeat directory {repeat_dir.name} must contain each frozen case once"
        )
    return config, {str(row["case_id"]): row for row in raw_rows}


def _copy_report(
    source: Path | None,
    output_dir: Path,
    case_id: str,
    repeat_index: int,
) -> str | None:
    if source is None or not source.is_file():
        return None
    destination = output_dir / "reports" / case_id / f"repeat_{repeat_index}.md"
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, destination)
    return destination.relative_to(output_dir).as_posix()


def _main_observation(
    run: dict[str, Any],
    main_bundle_dir: Path,
    output_dir: Path,
) -> dict[str, Any]:
    compact = deepcopy(run)
    case_id = str(compact["case_id"])
    compact["repeat_index"] = 1
    compact["stability_run_id"] = f"{case_id}:repeat-1"
    compact["stability_source"] = "published_main_v2"
    published_report = compact.get("published_report")
    report_source = (
        main_bundle_dir / str(published_report) if published_report else None
    )
    compact["published_report"] = _copy_report(report_source, output_dir, case_id, 1)
    return compact


def _repeat_observation(
    case: dict[str, Any],
    raw: dict[str, Any],
    repeat_dir: Path,
    output_dir: Path,
    repeat_index: int,
) -> dict[str, Any]:
    case_id = str(case["id"])
    metadata = raw.get("metadata") or {}
    workspace = repeat_dir / "workspaces" / case_id / "workspace"
    if metadata and workspace.is_dir():
        score = score_workspace(
            workspace,
            case,
            metadata,
            final_text=raw.get("final_text"),
        )
        status = "completed" if score["completed"] else "agent_failure"
        failure_type = None if score["completed"] else "acceptance_criteria"
    else:
        score = raw.get("score") or {}
        status = str(raw.get("status") or "infrastructure_failure")
        failure_type = raw.get("failure_type")

    report_source: Path | None = None
    report_paths = (score.get("artifact_files") or {}).get("report") or []
    if report_paths and workspace.is_dir():
        report_source = workspace / report_paths[-1]
    usage = metadata.get("usage") or {}
    calls = {field: metadata.get(field) for field in CALL_FIELDS}
    calls["llm_calls"] = usage.get("llm_calls")
    return {
        "case_id": case_id,
        "category": case.get("category"),
        "language": case.get("language"),
        "repeat_index": repeat_index,
        "stability_run_id": f"{case_id}:repeat-{repeat_index}",
        "stability_source": "additional_repeat",
        "source_result_dir": repeat_dir.name,
        "started_at": raw.get("started_at"),
        "finished_at": raw.get("finished_at"),
        "original_status": raw.get("status"),
        "original_failure_type": raw.get("failure_type"),
        "status": status,
        "failure_type": failure_type,
        "rescored": bool(metadata and workspace.is_dir()),
        "status_changed_by_rescore": status != raw.get("status"),
        "langfuse_trace_id": raw.get("langfuse_trace_id"),
        "latency_ms": raw.get("latency_ms"),
        "usage": {
            "llm_calls": usage.get("llm_calls"),
            "input_tokens": usage.get("input_tokens"),
            "output_tokens": usage.get("output_tokens"),
            "total_tokens": usage.get("total_tokens"),
        },
        "calls": calls,
        "score": score,
        "published_report": _copy_report(
            report_source, output_dir, case_id, repeat_index
        ),
    }


def _task_summary(case_id: str, rows: list[dict[str, Any]]) -> dict[str, Any]:
    ordered = sorted(rows, key=lambda row: int(row["repeat_index"]))
    statuses = [str(row["status"]) for row in ordered]
    completion_flags = [status == "completed" for status in statuses]
    completed_runs = sum(completion_flags)
    metric_values: dict[str, list[int | float]] = {
        "tokens": [
            int(row["usage"]["total_tokens"])
            for row in ordered
            if row.get("usage", {}).get("total_tokens") is not None
        ],
        "latency_ms": [
            int(row["latency_ms"])
            for row in ordered
            if row.get("latency_ms") is not None
        ],
    }
    calls = {
        field: _numeric_stats(
            [
                int(row["calls"][field])
                for row in ordered
                if row.get("calls", {}).get(field) is not None
            ],
            expected_count=3,
        )
        for field in CALL_FIELDS
    }
    return {
        "case_id": case_id,
        "statuses": statuses,
        "failure_types": [row.get("failure_type") for row in ordered],
        "completed_runs": completed_runs,
        "completion_frequency": _round(completed_runs / 3),
        "completion_agreement": len(set(completion_flags)) == 1,
        "exact_status_agreement": len(set(statuses)) == 1,
        "tokens": _numeric_stats(metric_values["tokens"], expected_count=3),
        "latency_ms": _numeric_stats(metric_values["latency_ms"], expected_count=3),
        "calls": calls,
    }


def _build_summary(rows: list[dict[str, Any]], case_ids: list[str]) -> dict[str, Any]:
    by_case: dict[str, list[dict[str, Any]]] = {case_id: [] for case_id in case_ids}
    for row in rows:
        by_case[str(row["case_id"])].append(row)
    per_task = [_task_summary(case_id, by_case[case_id]) for case_id in case_ids]
    statuses = Counter(str(row["status"]) for row in rows)
    completion_distribution = Counter(
        f"{task['completed_runs']}/3" for task in per_task
    )
    token_values = [
        int(row["usage"]["total_tokens"])
        for row in rows
        if row.get("usage", {}).get("total_tokens") is not None
    ]
    latency_values = [
        int(row["latency_ms"]) for row in rows if row.get("latency_ms") is not None
    ]
    return {
        "task_count": len(case_ids),
        "repeat_count": 3,
        "observation_count": len(rows),
        "completed_observation_count": statuses["completed"],
        "pooled_completion_rate": _round(statuses["completed"] / len(rows)),
        "status_counts": {
            status: statuses[status]
            for status in ("completed", "agent_failure", "infrastructure_failure")
        },
        "completion_agreement": {
            "all_three_agree_count": sum(
                bool(task["completion_agreement"]) for task in per_task
            ),
            "rate": _round(
                sum(bool(task["completion_agreement"]) for task in per_task)
                / len(per_task)
            ),
            "mixed_outcome_count": sum(
                not bool(task["completion_agreement"]) for task in per_task
            ),
            "all_three_completed_count": sum(
                task["completed_runs"] == 3 for task in per_task
            ),
            "all_three_not_completed_count": sum(
                task["completed_runs"] == 0 for task in per_task
            ),
            "frequency_distribution": dict(sorted(completion_distribution.items())),
        },
        "exact_status_agreement": {
            "all_three_agree_count": sum(
                bool(task["exact_status_agreement"]) for task in per_task
            ),
            "rate": _round(
                sum(bool(task["exact_status_agreement"]) for task in per_task)
                / len(per_task)
            ),
        },
        "tokens": _numeric_stats(token_values, expected_count=len(rows)),
        "latency_ms": _numeric_stats(latency_values, expected_count=len(rows)),
        "per_task": per_task,
        "cost": {
            "status": "pending_langfuse_collection",
            "note": "The ten main-v2 observations are reused; only twenty additional observations are newly paid runs.",
        },
    }


def _format_optional(value: Any, *, percent: bool = False) -> str:
    if value is None:
        return "n/a"
    return f"{float(value):.1%}" if percent else f"{float(value):.1f}"


def _write_report(
    output_dir: Path,
    config: dict[str, Any],
    summary: dict[str, Any],
) -> None:
    rows = []
    for task in summary["per_task"]:
        rows.append(
            "| {case_id} | {completed}/3 | {statuses} | {agreement} | {token_cv} | {latency_cv} | {search_range} | {researcher_range} |".format(
                case_id=task["case_id"],
                completed=task["completed_runs"],
                statuses=" / ".join(task["statuses"]),
                agreement="yes" if task["completion_agreement"] else "no",
                token_cv=_format_optional(
                    task["tokens"]["coefficient_of_variation"], percent=True
                ),
                latency_cv=_format_optional(
                    task["latency_ms"]["coefficient_of_variation"], percent=True
                ),
                search_range=_format_optional(task["calls"]["search_calls"]["range"]),
                researcher_range=_format_optional(
                    task["calls"]["researcher_calls"]["range"]
                ),
            )
        )
    agreement = summary["completion_agreement"]
    report = "\n".join(
        [
            "# Published Deep Research v2 Stability Evaluation",
            "",
            f"- Parent protocol: `{config['protocol_version']}`",
            f"- Model: `{config['model_name']}`",
            f"- Dataset SHA-256: `{config['dataset_sha256']}`",
            f"- Subset SHA-256: `{config['subset_sha256']}`",
            f"- Tasks: {summary['task_count']}",
            f"- Observations: {summary['observation_count']}",
            "- Cost status: pending Langfuse export",
            "",
            "## Stability Summary",
            "",
            (
                f"- Three-run completion agreement: {agreement['all_three_agree_count']}/"
                f"{summary['task_count']} ({agreement['rate']:.1%})."
            ),
            (
                f"- Three-run exact-status agreement: "
                f"{summary['exact_status_agreement']['all_three_agree_count']}/"
                f"{summary['task_count']} "
                f"({summary['exact_status_agreement']['rate']:.1%})."
            ),
            f"- Mixed completion outcomes: {agreement['mixed_outcome_count']} tasks.",
            (
                f"- Pooled completion: {summary['completed_observation_count']}/"
                f"{summary['observation_count']} "
                f"({summary['pooled_completion_rate']:.1%}); these observations are "
                "clustered within ten tasks."
            ),
            "",
            "| Case | Completed | Statuses | Completion agreement | Token CV | Latency CV | Search-call range | Researcher-call range |",
            "| --- | ---: | --- | --- | ---: | ---: | ---: | ---: |",
            *rows,
            "",
            "## Audit Notes",
            "",
            "- Repeat 1 reuses the immutable published `main_v2` observation.",
            "- Repeats 2 and 3 are rescored from their original workspaces when available.",
            "- Every selected task has exactly three observations and every trace ID is unique.",
            "- The subset was frozen after the main regression run and is not holdout evidence.",
            "- Raw result directories are not modified by publication.",
            "- Structural completion does not establish factual correctness or citation entailment.",
            "",
        ]
    )
    (output_dir / "report.md").write_text(report, encoding="utf-8")


def publish_stability(
    dataset_path: Path,
    subset_path: Path,
    main_bundle_dir: Path,
    repeat_dirs: list[Path],
    output_dir: Path,
    *,
    published_at: str | None = None,
) -> dict[str, Any]:
    if len(repeat_dirs) != 2:
        raise ValueError(
            "stability publication requires exactly two repeat directories"
        )
    subset_validation = validate_stability_subset(dataset_path, subset_path)
    main_config, main_runs, main_source_configs = _load_main_bundle(
        main_bundle_dir, subset_validation
    )
    main_by_id = {str(run["case_id"]): run for run in main_runs}
    case_ids = subset_validation["case_ids"]
    baseline_config = main_source_configs[case_ids[0]]
    _validate_compatible_configs(
        baseline_config,
        [
            (f"main source {case_id}", main_source_configs[case_id])
            for case_id in case_ids[1:]
        ],
    )

    loaded_repeats = [
        _load_repeat_dir(repeat_dir, case_ids) for repeat_dir in repeat_dirs
    ]
    _validate_compatible_configs(
        baseline_config,
        [
            (f"repeat directory {repeat_dir.name}", loaded_repeats[index][0])
            for index, repeat_dir in enumerate(repeat_dirs)
        ],
    )
    if output_dir.exists():
        raise FileExistsError(f"stability output already exists: {output_dir}")
    output_dir.mkdir(parents=True)

    observations: list[dict[str, Any]] = []
    for case_id in case_ids:
        observations.append(
            _main_observation(main_by_id[case_id], main_bundle_dir, output_dir)
        )
        case = subset_validation["case_by_id"][case_id]
        for offset, repeat_dir in enumerate(repeat_dirs, start=2):
            observations.append(
                _repeat_observation(
                    case,
                    loaded_repeats[offset - 2][1][case_id],
                    repeat_dir,
                    output_dir,
                    offset,
                )
            )

    run_ids = [str(row["stability_run_id"]) for row in observations]
    if len(run_ids) != 30 or len(set(run_ids)) != 30:
        raise ValueError("stability observations must contain 30 unique run IDs")
    trace_ids = [str(row.get("langfuse_trace_id") or "") for row in observations]
    if any(not trace_id for trace_id in trace_ids) or len(set(trace_ids)) != 30:
        raise ValueError("stability observations must contain 30 unique trace IDs")

    summary = _build_summary(observations, case_ids)
    timestamp = published_at or datetime.now(UTC).isoformat()
    observed_git_commits = sorted(
        {
            str(config.get("git_commit") or "unknown")
            for config in [baseline_config, *[item[0] for item in loaded_repeats]]
        }
    )
    config = {
        "publication_schema_version": 1,
        "published_at": timestamp,
        "dataset_name": "research_stability_v2",
        "dataset_sha256": subset_validation["dataset_sha256"],
        "subset_sha256": subset_validation["subset_sha256"],
        "subset_version": subset_validation["subset"]["version"],
        "protocol_version": main_config["protocol_version"],
        "model_name": main_config["model_name"],
        "run_date": baseline_config["run_date"],
        "selected_case_ids": case_ids,
        "repeat_count": 3,
        "main_bundle": _display_path(main_bundle_dir),
        "repeat_result_dirs": [_display_path(repeat_dir) for repeat_dir in repeat_dirs],
        "source_git_commits": observed_git_commits,
        "selection_chronology": subset_validation["subset"]["selection_policy"][
            "chronology"
        ],
    }
    source_manifest = {
        "main_bundle_config_sha256": _sha256(main_bundle_dir / "config.json"),
        "main_bundle_runs_sha256": _sha256(main_bundle_dir / "rescored_runs.jsonl"),
        "repeat_directories": [
            {
                "path": _display_path(repeat_dir),
                "config_sha256": _sha256(repeat_dir / "config.json"),
                "raw_runs_sha256": _sha256(repeat_dir / "raw_runs.jsonl"),
            }
            for repeat_dir in repeat_dirs
        ],
    }
    _write_json(output_dir / "config.json", config)
    _write_jsonl(output_dir / "rescored_runs.jsonl", observations)
    _write_json(output_dir / "summary.json", summary)
    _write_report(output_dir, config, summary)
    manifest = {
        "publication_schema_version": 1,
        "published_at": timestamp,
        "dataset_sha256": subset_validation["dataset_sha256"],
        "subset_sha256": subset_validation["subset_sha256"],
        "sources": source_manifest,
        "outputs": {
            "config.json": _sha256(output_dir / "config.json"),
            "rescored_runs.jsonl": _sha256(output_dir / "rescored_runs.jsonl"),
            "summary.json": _sha256(output_dir / "summary.json"),
            "report.md": _sha256(output_dir / "report.md"),
        },
    }
    _write_json(output_dir / "manifest.json", manifest)
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate or publish the Deep Research v2 stability subset"
    )
    parser.add_argument("--dataset", default="evals/datasets/research_main_v1.jsonl")
    parser.add_argument("--subset", default="evals/stability_subset_v1.json")
    parser.add_argument("--main-bundle", default="evals/results/published/main_v2")
    parser.add_argument("--repeat-dir", action="append", default=[])
    parser.add_argument("--output-dir", default="evals/results/published/stability_v2")
    parser.add_argument("--validate-subset-only", action="store_true")
    parser.add_argument("--validate-preflight", action="store_true")
    args = parser.parse_args()

    dataset_path = (PROJECT_ROOT / args.dataset).resolve()
    subset_path = (PROJECT_ROOT / args.subset).resolve()
    main_bundle_dir = (PROJECT_ROOT / args.main_bundle).resolve()
    if args.validate_subset_only:
        validation = validate_stability_subset(dataset_path, subset_path)
        print(
            json.dumps(
                {
                    key: value
                    for key, value in validation.items()
                    if key not in {"subset", "case_by_id"}
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return 0
    if args.validate_preflight:
        print(
            json.dumps(
                validate_stability_preflight(
                    dataset_path,
                    subset_path,
                    main_bundle_dir,
                ),
                ensure_ascii=False,
                indent=2,
            )
        )
        return 0
    if len(args.repeat_dir) != 2:
        parser.error("provide exactly two --repeat-dir values")
    summary = publish_stability(
        dataset_path,
        subset_path,
        main_bundle_dir,
        [(PROJECT_ROOT / path).resolve() for path in args.repeat_dir],
        (PROJECT_ROOT / args.output_dir).resolve(),
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
