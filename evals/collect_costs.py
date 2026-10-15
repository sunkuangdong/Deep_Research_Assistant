from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import re
from collections import defaultdict
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PUBLISHED_DIR = Path("evals/results/published/smoke_v1")
COST_SECTION_START = "<!-- cost-evidence:start -->"
COST_SECTION_END = "<!-- cost-evidence:end -->"


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


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _decimal(value: Any) -> Decimal:
    if value is None:
        return Decimal(0)
    return Decimal(str(value))


def _number(value: Decimal, places: int = 12) -> float:
    quantum = Decimal(1).scaleb(-places)
    return float(value.quantize(quantum))


def _get_field(value: Any, name: str, default: Any = None) -> Any:
    if isinstance(value, dict):
        if name in value:
            return value[name]
        camel_name = "".join(
            part if index == 0 else part.title()
            for index, part in enumerate(name.split("_"))
        )
        return value.get(camel_name, default)
    return getattr(value, name, default)


def _fetch_generations(client: Any, trace_id: str) -> list[Any]:
    observations: list[Any] = []
    cursor: str | None = None
    while True:
        response = client.api.observations.get_many(
            trace_id=trace_id,
            type="GENERATION",
            fields="basic,usage,model",
            limit=1000,
            cursor=cursor,
        )
        observations.extend(_get_field(response, "data", []))
        meta = _get_field(response, "meta")
        next_cursor = _get_field(meta, "cursor") if meta is not None else None
        if not next_cursor:
            break
        if next_cursor == cursor:
            raise ValueError(f"Langfuse returned a repeated cursor for trace {trace_id}")
        cursor = str(next_cursor)
    return observations


def _collect_trace_cost(
    client: Any,
    run: dict[str, Any],
) -> dict[str, Any]:
    case_id = str(run.get("case_id") or "")
    trace_id = str(run.get("langfuse_trace_id") or "")
    if not trace_id:
        raise ValueError(f"published run {case_id} has no Langfuse trace ID")

    generations = _fetch_generations(client, trace_id)
    expected_calls = run.get("usage", {}).get("llm_calls")
    if expected_calls is None:
        raise ValueError(f"published run {case_id} has no llm_calls metric")
    if len(generations) != int(expected_calls):
        raise ValueError(
            f"trace {trace_id} has {len(generations)} generations, "
            f"but {case_id} records {expected_calls} llm_calls"
        )

    total_cost = Decimal(0)
    component_costs: dict[str, Decimal] = defaultdict(lambda: Decimal(0))
    models: set[str] = set()
    unpriced_observation_ids: list[str] = []
    for observation in generations:
        observation_id = str(_get_field(observation, "id") or "unknown")
        observation_cost = _get_field(observation, "total_cost")
        if observation_cost is None:
            unpriced_observation_ids.append(observation_id)
            continue
        total_cost += _decimal(observation_cost)
        model = _get_field(observation, "model")
        if model:
            models.add(str(model))
        for key, value in (_get_field(observation, "cost_details", {}) or {}).items():
            component_costs[str(key)] += _decimal(value)

    if unpriced_observation_ids:
        raise ValueError(
            f"trace {trace_id} contains unpriced generations: "
            + ", ".join(unpriced_observation_ids)
        )

    search_calls = run.get("calls", {}).get("search_calls")
    if search_calls is None:
        raise ValueError(f"published run {case_id} has no search_calls metric")

    return {
        "case_id": case_id,
        "langfuse_trace_id": trace_id,
        "models": sorted(models),
        "generation_count": len(generations),
        "priced_generation_count": len(generations),
        "total_cost_usd": _number(total_cost),
        "cost_components_usd": {
            key: _number(value) for key, value in sorted(component_costs.items())
        },
        "local_total_tokens": run.get("usage", {}).get("total_tokens"),
        "local_search_calls": int(search_calls),
    }


def _build_cost_evidence(
    runs: list[dict[str, Any]],
    per_trace: list[dict[str, Any]],
    *,
    bocha_package_price_cny: Decimal,
    bocha_package_calls: int,
    bocha_remaining_calls: int | None,
    target_run_count: int,
    projection_buffer: Decimal,
    model_spend_cap_usd: Decimal,
    search_call_cap: int,
    openai_credit_balance_usd: Decimal | None,
    balance_snapshot_date: str | None,
    collected_at: str,
) -> dict[str, Any]:
    run_count = len(runs)
    if run_count == 0:
        raise ValueError("published bundle contains no runs")
    if bocha_package_calls <= 0:
        raise ValueError("Bocha package call count must be positive")
    if target_run_count <= 0:
        raise ValueError("target run count must be positive")
    if projection_buffer < 1:
        raise ValueError("projection buffer must be at least 1.0")

    total_model_cost = sum(
        (_decimal(item["total_cost_usd"]) for item in per_trace),
        Decimal(0),
    )
    mean_model_cost = total_model_cost / Decimal(run_count)
    projected_model_cost = mean_model_cost * Decimal(target_run_count)
    buffered_model_cost = projected_model_cost * projection_buffer

    total_search_calls = sum(item["local_search_calls"] for item in per_trace)
    mean_search_calls = Decimal(total_search_calls) / Decimal(run_count)
    projected_search_calls = math.ceil(
        mean_search_calls * Decimal(target_run_count) * projection_buffer
    )
    bocha_unit_cost = bocha_package_price_cny / Decimal(bocha_package_calls)
    allocated_bocha_cost = bocha_unit_cost * Decimal(total_search_calls)
    projected_bocha_cost = bocha_unit_cost * Decimal(projected_search_calls)

    component_totals: dict[str, Decimal] = defaultdict(lambda: Decimal(0))
    for item in per_trace:
        for key, value in item["cost_components_usd"].items():
            component_totals[key] += _decimal(value)

    evidence: dict[str, Any] = {
        "schema_version": 1,
        "collected_at": collected_at,
        "source": {
            "model_costs": "Langfuse Observations v2 GENERATION records",
            "run_metrics": "published rescored_runs.jsonl",
            "bocha_pricing": "manual package configuration",
            "dashboard_snapshots": "capacity audit only; not run-cost evidence",
        },
        "validation": {
            "trace_count": len(per_trace),
            "all_generation_counts_match_local_llm_calls": True,
            "all_generations_priced": True,
            "root_observations_excluded": True,
        },
        "model_cost": {
            "currency": "USD",
            "run_count": run_count,
            "total_usd": _number(total_model_cost),
            "mean_per_run_usd": _number(mean_model_cost),
            "cost_components_usd": {
                key: _number(value)
                for key, value in sorted(component_totals.items())
            },
            "target_run_count": target_run_count,
            "projection_buffer_multiplier": float(projection_buffer),
            "projected_target_cost_usd": _number(projected_model_cost),
            "projected_target_cost_with_buffer_usd": _number(buffered_model_cost),
            "spend_cap_usd": _number(model_spend_cap_usd),
            "within_spend_cap": buffered_model_cost <= model_spend_cap_usd,
            "cap_headroom_usd": _number(model_spend_cap_usd - buffered_model_cost),
        },
        "bocha_search_cost": {
            "currency": "CNY",
            "package_price_cny": _number(bocha_package_price_cny, 4),
            "package_calls": bocha_package_calls,
            "unit_cost_cny": _number(bocha_unit_cost, 8),
            "smoke_search_calls": total_search_calls,
            "smoke_allocated_cost_cny": _number(allocated_bocha_cost, 4),
            "projected_target_calls_with_buffer": projected_search_calls,
            "projected_target_allocated_cost_cny": _number(
                projected_bocha_cost, 4
            ),
            "search_call_cap": search_call_cap,
            "within_search_call_cap": projected_search_calls <= search_call_cap,
        },
        "per_trace": per_trace,
    }
    if bocha_remaining_calls is not None:
        evidence["bocha_search_cost"]["remaining_calls_snapshot"] = (
            bocha_remaining_calls
        )
        evidence["bocha_search_cost"]["remaining_calls_cover_projection"] = (
            bocha_remaining_calls >= projected_search_calls
        )
    if openai_credit_balance_usd is not None:
        evidence["capacity_snapshot"] = {
            "snapshot_date": balance_snapshot_date,
            "openai_credit_balance_usd": _number(openai_credit_balance_usd),
            "credit_balance_covers_projection": (
                openai_credit_balance_usd >= buffered_model_cost
            ),
        }
    return evidence


def _cost_summary(evidence: dict[str, Any]) -> dict[str, Any]:
    model = evidence["model_cost"]
    bocha = evidence["bocha_search_cost"]
    return {
        "status": "collected",
        "source": "Langfuse GENERATION observations plus local search-call metrics",
        "collected_at": evidence["collected_at"],
        "total_usd": model["total_usd"],
        "mean_per_run_usd": model["mean_per_run_usd"],
        "projected_50_run_cost_usd": model["projected_target_cost_usd"],
        "projected_50_run_cost_with_20_percent_buffer_usd": model[
            "projected_target_cost_with_buffer_usd"
        ],
        "model_spend_cap_usd": model["spend_cap_usd"],
        "within_model_spend_cap": model["within_spend_cap"],
        "bocha_smoke_search_calls": bocha["smoke_search_calls"],
        "bocha_smoke_allocated_cost_cny": bocha["smoke_allocated_cost_cny"],
        "projected_50_run_search_calls_with_20_percent_buffer": bocha[
            "projected_target_calls_with_buffer"
        ],
        "search_call_cap": bocha["search_call_cap"],
        "within_search_call_cap": bocha["within_search_call_cap"],
    }


def _update_report(report_path: Path, evidence: dict[str, Any]) -> None:
    report = report_path.read_text(encoding="utf-8")
    model = evidence["model_cost"]
    bocha = evidence["bocha_search_cost"]
    report = re.sub(
        r"^- (?:Cost status|Model cost):.*$",
        f"- Model cost: ${model['total_usd']:.6f} across "
        f"{model['run_count']} smoke runs",
        report,
        count=1,
        flags=re.MULTILINE,
    )
    section = "\n".join(
        [
            COST_SECTION_START,
            "## Cost Evidence",
            "",
            (
                f"- Langfuse model cost: ${model['total_usd']:.6f} total; "
                f"${model['mean_per_run_usd']:.6f} mean per run."
            ),
            (
                f"- Projected model cost for {model['target_run_count']} runs: "
                f"${model['projected_target_cost_usd']:.6f}; "
                f"${model['projected_target_cost_with_buffer_usd']:.6f} with the "
                f"{model['projection_buffer_multiplier']:.0%} multiplier."
            ),
            (
                f"- Model spend cap: ${model['spend_cap_usd']:.2f}; "
                f"within cap: {str(model['within_spend_cap']).lower()}."
            ),
            (
                f"- Bocha smoke usage: {bocha['smoke_search_calls']} calls, "
                f"allocated cost CNY {bocha['smoke_allocated_cost_cny']:.4f}."
            ),
            (
                "- Projected Bocha usage: "
                f"{bocha['projected_target_calls_with_buffer']} calls with buffer; "
                f"cap {bocha['search_call_cap']} calls."
            ),
            (
                "- Root observations are excluded; model cost is summed only from "
                "priced `GENERATION` observations."
            ),
            "- Full trace-level evidence is stored in `costs.json`.",
            COST_SECTION_END,
        ]
    )
    if COST_SECTION_START in report and COST_SECTION_END in report:
        before, remainder = report.split(COST_SECTION_START, 1)
        _, after = remainder.split(COST_SECTION_END, 1)
        report = before.rstrip() + "\n\n" + section + after
    elif "\n## Audit Notes" in report:
        report = report.replace("\n## Audit Notes", f"\n{section}\n\n## Audit Notes")
    else:
        report = report.rstrip() + "\n\n" + section + "\n"
    report_path.write_text(report, encoding="utf-8")


def collect_costs(
    published_dir: Path,
    client: Any,
    *,
    bocha_package_price_cny: Decimal,
    bocha_package_calls: int,
    bocha_remaining_calls: int | None = None,
    target_run_count: int = 50,
    projection_buffer: Decimal = Decimal("1.2"),
    model_spend_cap_usd: Decimal = Decimal("1.5"),
    search_call_cap: int = 360,
    openai_credit_balance_usd: Decimal | None = None,
    balance_snapshot_date: str | None = None,
    collected_at: str | None = None,
) -> dict[str, Any]:
    runs_path = published_dir / "rescored_runs.jsonl"
    summary_path = published_dir / "summary.json"
    report_path = published_dir / "report.md"
    manifest_path = published_dir / "manifest.json"
    for required in (runs_path, summary_path, report_path, manifest_path):
        if not required.is_file():
            raise FileNotFoundError(f"missing published artifact: {required}")

    runs = _read_jsonl(runs_path)
    per_trace = [_collect_trace_cost(client, run) for run in runs]
    evidence = _build_cost_evidence(
        runs,
        per_trace,
        bocha_package_price_cny=bocha_package_price_cny,
        bocha_package_calls=bocha_package_calls,
        bocha_remaining_calls=bocha_remaining_calls,
        target_run_count=target_run_count,
        projection_buffer=projection_buffer,
        model_spend_cap_usd=model_spend_cap_usd,
        search_call_cap=search_call_cap,
        openai_credit_balance_usd=openai_credit_balance_usd,
        balance_snapshot_date=balance_snapshot_date,
        collected_at=collected_at or datetime.now(UTC).isoformat(),
    )

    summary = _read_json(summary_path)
    summary["cost"] = _cost_summary(evidence)
    _write_json(published_dir / "costs.json", evidence)
    _write_json(summary_path, summary)
    _update_report(report_path, evidence)
    manifest = _read_json(manifest_path)
    manifest["cost_evidence"] = {
        "collected_at": evidence["collected_at"],
        "costs_sha256": _sha256(published_dir / "costs.json"),
        "summary_sha256": _sha256(summary_path),
        "report_sha256": _sha256(report_path),
    }
    _write_json(manifest_path, manifest)
    return evidence


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Collect Langfuse model costs for a published evaluation bundle"
    )
    parser.add_argument("--published-dir", default=str(DEFAULT_PUBLISHED_DIR))
    parser.add_argument("--bocha-package-price-cny", type=Decimal, required=True)
    parser.add_argument("--bocha-package-calls", type=int, required=True)
    parser.add_argument("--bocha-remaining-calls", type=int)
    parser.add_argument("--target-run-count", type=int, default=50)
    parser.add_argument("--projection-buffer", type=Decimal, default=Decimal("1.2"))
    parser.add_argument(
        "--model-spend-cap-usd", type=Decimal, default=Decimal("1.5")
    )
    parser.add_argument("--search-call-cap", type=int, default=360)
    parser.add_argument("--openai-credit-balance-usd", type=Decimal)
    parser.add_argument("--balance-snapshot-date")
    args = parser.parse_args()

    load_dotenv(PROJECT_ROOT / ".env", override=True)
    required_env = ("LANGFUSE_PUBLIC_KEY", "LANGFUSE_SECRET_KEY")
    missing = [name for name in required_env if not os.getenv(name)]
    if missing:
        raise ValueError("missing Langfuse environment variables: " + ", ".join(missing))

    from langfuse import get_client

    evidence = collect_costs(
        (PROJECT_ROOT / args.published_dir).resolve(),
        get_client(),
        bocha_package_price_cny=args.bocha_package_price_cny,
        bocha_package_calls=args.bocha_package_calls,
        bocha_remaining_calls=args.bocha_remaining_calls,
        target_run_count=args.target_run_count,
        projection_buffer=args.projection_buffer,
        model_spend_cap_usd=args.model_spend_cap_usd,
        search_call_cap=args.search_call_cap,
        openai_credit_balance_usd=args.openai_credit_balance_usd,
        balance_snapshot_date=args.balance_snapshot_date,
    )
    print(json.dumps(evidence, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
