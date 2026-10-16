from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace

import pytest

from evals.collect_costs import collect_costs


class FakeObservations:
    def __init__(
        self,
        observations_by_trace: dict[str, list[dict]],
        tools_by_trace: dict[str, list[dict]] | None = None,
    ):
        self.observations_by_trace = observations_by_trace
        self.tools_by_trace = tools_by_trace or {}

    def get_many(self, **kwargs):
        trace_id = kwargs["trace_id"]
        if kwargs["type"] == "GENERATION":
            assert kwargs["fields"] == "basic,usage,model"
            data = self.observations_by_trace[trace_id]
        else:
            assert kwargs["type"] == "TOOL"
            assert kwargs["fields"] == "basic"
            data = self.tools_by_trace.get(trace_id, [])
        return SimpleNamespace(
            data=data,
            meta=SimpleNamespace(cursor=None),
        )


def _client(
    observations_by_trace: dict[str, list[dict]],
    tools_by_trace: dict[str, list[dict]] | None = None,
):
    return SimpleNamespace(
        api=SimpleNamespace(
            observations=FakeObservations(observations_by_trace, tools_by_trace)
        )
    )


def _published_bundle(
    tmp_path: Path,
    dataset_name: str = "research_main_v1",
) -> Path:
    published = tmp_path / "published"
    published.mkdir()
    runs = [
        {
            "case_id": "case-1",
            "langfuse_trace_id": "trace-1",
            "usage": {"llm_calls": 2, "total_tokens": 100},
            "calls": {"search_calls": 3},
        },
        {
            "case_id": "case-2",
            "langfuse_trace_id": "trace-2",
            "usage": {"llm_calls": 1, "total_tokens": 50},
            "calls": {"search_calls": 1},
        },
    ]
    (published / "rescored_runs.jsonl").write_text(
        "".join(json.dumps(run) + "\n" for run in runs), encoding="utf-8"
    )
    (published / "summary.json").write_text(
        json.dumps({"run_count": 2, "cost": {"status": "pending"}}),
        encoding="utf-8",
    )
    (published / "report.md").write_text(
        "# Report\n\n- Cost status: pending Langfuse export\n\n## Audit Notes\n",
        encoding="utf-8",
    )
    (published / "manifest.json").write_text("{}\n", encoding="utf-8")
    (published / "config.json").write_text(
        json.dumps({"dataset_name": dataset_name}), encoding="utf-8"
    )
    return published


def test_collect_costs_updates_published_evidence(tmp_path: Path):
    published = _published_bundle(tmp_path)
    client = _client(
        {
            "trace-1": [
                {
                    "id": "gen-1",
                    "model": "model-a",
                    "totalCost": 0.01,
                    "costDetails": {"input": 0.004, "output": 0.006},
                },
                {
                    "id": "gen-2",
                    "model": "model-a",
                    "total_cost": 0.02,
                    "cost_details": {"input": 0.005, "output": 0.015},
                },
            ],
            "trace-2": [
                {
                    "id": "gen-3",
                    "model": "model-a",
                    "total_cost": 0.03,
                    "cost_details": {"input": 0.01, "output": 0.02},
                }
            ],
        }
    )

    evidence = collect_costs(
        published,
        client,
        bocha_package_price_cny=Decimal("3.6"),
        bocha_package_calls=1000,
        bocha_remaining_calls=934,
        target_run_count=50,
        projection_buffer=Decimal("1.2"),
        model_spend_cap_usd=Decimal("2.0"),
        search_call_cap=360,
        openai_credit_balance_usd=Decimal("5.82"),
        balance_snapshot_date="2026-10-15",
        collected_at="2026-10-15T00:00:00+00:00",
    )

    assert evidence["model_cost"]["total_usd"] == 0.06
    assert evidence["model_cost"]["mean_per_run_usd"] == 0.03
    assert evidence["model_cost"]["projected_target_cost_with_buffer_usd"] == 1.8
    assert evidence["model_cost"]["within_spend_cap"] is True
    assert evidence["evaluation_scope"] == "main benchmark"
    assert evidence["bocha_search_cost"]["evaluation_search_calls"] == 4
    assert evidence["bocha_search_cost"]["evaluation_allocated_cost_cny"] == 0.0144
    assert evidence["bocha_search_cost"]["projected_target_calls_with_buffer"] == 120
    assert evidence["capacity_snapshot"]["credit_balance_covers_projection"] is True

    saved = json.loads((published / "costs.json").read_text(encoding="utf-8"))
    summary = json.loads((published / "summary.json").read_text(encoding="utf-8"))
    manifest = json.loads((published / "manifest.json").read_text(encoding="utf-8"))
    report = (published / "report.md").read_text(encoding="utf-8")
    assert saved == evidence
    assert summary["cost"]["status"] == "collected"
    assert summary["cost"]["total_usd"] == 0.06
    assert "## Cost Evidence" in report
    assert "across 2 main benchmark runs" in report
    assert "Bocha main benchmark usage" in report
    assert "smoke runs" not in report
    assert "Root observations are excluded" in report
    assert len(manifest["cost_evidence"]["costs_sha256"]) == 64
    assert len(manifest["cost_evidence"]["summary_sha256"]) == 64
    assert len(manifest["cost_evidence"]["report_sha256"]) == 64


def test_collect_costs_rejects_generation_count_mismatch(tmp_path: Path):
    published = _published_bundle(tmp_path)
    client = _client(
        {
            "trace-1": [{"id": "gen-1", "model": "model-a", "total_cost": 0.01}],
            "trace-2": [{"id": "gen-2", "model": "model-a", "total_cost": 0.01}],
        }
    )

    with pytest.raises(ValueError, match="2 llm_calls"):
        collect_costs(
            published,
            client,
            bocha_package_price_cny=Decimal("3.6"),
            bocha_package_calls=1000,
        )

    assert not (published / "costs.json").exists()


def test_collect_costs_recovers_metrics_for_terminal_failure(tmp_path: Path):
    published = _published_bundle(tmp_path)
    runs_path = published / "rescored_runs.jsonl"
    runs = [json.loads(line) for line in runs_path.read_text().splitlines()]
    runs[1].update(
        {
            "status": "agent_failure",
            "failure_type": "recursion_limit",
            "original_failure_type": "recursion_limit",
            "usage": {
                "llm_calls": None,
                "total_tokens": None,
            },
            "calls": {"search_calls": None},
        }
    )
    runs_path.write_text(
        "".join(json.dumps(run) + "\n" for run in runs),
        encoding="utf-8",
    )
    client = _client(
        {
            "trace-1": [
                {"id": "gen-1", "model": "model-a", "total_cost": 0.01},
                {"id": "gen-2", "model": "model-a", "total_cost": 0.02},
            ],
            "trace-2": [
                {"id": "gen-3", "model": "model-a", "total_cost": 0.03},
                {"id": "gen-4", "model": "model-a", "total_cost": 0.04},
            ],
        },
        {
            "trace-2": [
                {"id": "tool-1", "name": "web_search"},
                {"id": "tool-2", "name": "write_file"},
                {"id": "tool-3", "name": "bocha_web_search"},
            ]
        },
    )

    evidence = collect_costs(
        published,
        client,
        bocha_package_price_cny=Decimal("3.6"),
        bocha_package_calls=1000,
    )

    recovered = evidence["per_trace"][1]
    assert recovered["generation_count"] == 2
    assert recovered["local_llm_calls"] is None
    assert recovered["generation_count_matches_local_llm_calls"] is None
    assert recovered["search_calls"] == 2
    assert recovered["local_search_calls"] is None
    assert recovered["search_call_count_source"] == "langfuse_tool_observations"
    assert evidence["model_cost"]["total_usd"] == 0.1
    assert evidence["bocha_search_cost"]["evaluation_search_calls"] == 5
    assert (
        evidence["validation"]["all_generation_counts_match_local_llm_calls"] is False
    )
    assert (
        evidence["validation"]["all_available_generation_counts_match_local_llm_calls"]
        is True
    )
    assert evidence["validation"]["missing_local_llm_calls_case_ids"] == ["case-2"]
    assert evidence["validation"]["trace_derived_search_calls_case_ids"] == ["case-2"]
