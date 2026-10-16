# Deep Research Assistant Evaluation Protocol v2

- **Status:** FROZEN
- **Version:** 2.1.0
- **Protocol Owner:** Kuangdong Sun
- **Dataset Version:** v1 regression benchmark
- **Frozen At:** 2026-10-16
- **Last Updated:** 2026-10-16
- **Expected Git Tag:** `deep-research-eval-v2.1.0`

## Purpose

Protocol v2.1.0 measures whether deterministic evidence gates and bounded
citation recovery improve the completion reliability of the existing
file-handoff multi-agent research workflow. It preserves the v1.3.0 scoring
criteria and datasets so results can be compared case by case.

Because the v2 changes were designed after reviewing v1 failures, the repeated
30-case run is a regression benchmark, not an independent holdout evaluation.
It may establish that the observed v1 failure modes were repaired, but it must
not be presented as an unbiased estimate of generalization to unseen tasks.

## Relationship to v1.3.0

The following v1 artifacts remain immutable:

- `evals/EVALUATION_SPEC.md`
- `evals/datasets/research_smoke_v1.jsonl`
- `evals/datasets/research_main_v1.jsonl`
- `evals/results/published/smoke_v1/`
- `evals/results/published/main_v1/`

Protocol v2.1.0 changes the workflow and runtime guardrails, not the frozen
case labels or deterministic scoring rules.

## Locked v2 Changes

### P1: Evidence Inventory Gate

- Build a per-run inventory from URLs returned by `web_search` or a successful
  `web_fetch`.
- Treat a URL as eligible only when the canonical page also appears in a
  findings or analysis artifact from the same run.
- Block analyst delegation and draft creation until the case-specific minimum
  number of eligible source pages is available.
- Block final-report creation unless the report meets the minimum citation
  count and every citation belongs to the eligible allowlist.
- Record eligible, retrieved-only, and preserved-only pages plus every gate
  event in run metadata.

### P2: Planned Targets and Bounded Recovery

- Before the first researcher delegation, require `research_plan.md` to define
  at least the case-specific minimum number of distinct evidence targets.
- Each target uses this machine-readable form:

  ```text
  - target_id: source_1 | source_target: <unique page objective> | findings_path: /workspace/sources/findings_<slug>.md
  ```

- Reject duplicate target IDs, duplicate normalized source targets, invalid
  findings paths, and target-count deficits.
- Limit initial research to two researcher delegations.
- Reserve the third researcher delegation, final `web_search`, and final
  `web_fetch` for evidence recovery.
- Release the recovery researcher only after `check_evidence_inventory` reports
  a positive citation deficit and its task is marked `[EVIDENCE_RECOVERY]`.
- Require every findings artifact to contain `## Preserved Source URLs` with
  exact URLs and expose per-file URL inventories in run metadata.

## Frozen Dataset Fingerprints

```yaml
research_smoke_v1_sha256: 3ccaf7875e499bde0aaaa5f062aa0acafed6e02f00ddde264ed7f4dc5cf10f59
research_main_v1_sha256: 9595213afcdd0b7baedf00f948d8364560e7484378ad06f88c0ed44d356fbf42
```

## Success Criteria

A task is `completed` only when all v1.3.0 acceptance conditions pass:

1. The workflow terminates without an unhandled application error.
2. Every case-required artifact exists at a valid path.
3. The final report exists, has the explicit run date in its filename, and
   contains every required section.
4. The final report meets the case-specific distinct citation minimum.
5. Every citation is syntactically valid, preserved in findings or analysis,
   and retrieved during the same run.
6. Artifact, todo, final-response language, and all configured call budgets
   comply with the case and protocol.

The v2 research-plan and evidence-inventory checks are runtime constraints.
They do not replace or weaken final deterministic scoring.

## Frozen Runtime Configuration

```yaml
protocol_version: 2.1.0
provider: openai
model_name: gpt-6-luna
model_base_url: https://api.openai.com/v1
model_max_input_tokens: 131072
temperature: 0
reasoning_effort: none
timeout_seconds: 900
max_provider_retries: 2
concurrency: 1
deepagents_recursion_limit: 120
search_call_limit: 6
search_recovery_reserve: 1
search_timeout_seconds: 20
search_max_retries: 2
fetch_call_limit: 6
fetch_recovery_reserve: 1
fetch_timeout_seconds: 20
fetch_max_retries: 1
fetch_max_bytes: 200000
fetch_max_chars: 12000
researcher_call_limit: 3
researcher_initial_call_limit: 2
researcher_recovery_call_limit: 1
analyst_call_limit: 1
editor_call_limit: 1
draft_edit_call_limit: 1
evidence_inventory_gate: true
structured_research_plan_gate: true
```

## Pre-Freeze Validation Evidence

Four v1 failure cases were run once with the v2.1.0 release candidate:

| Case | v1 status | P1 status when tested | v2 status | Eligible sources | Recovery researcher |
| --- | --- | --- | --- | ---: | ---: |
| `dr-main-001` | failed | completed | completed | 5/5 | 1 |
| `dr-main-014` | failed | completed | completed | 5/5 | 1 |
| `dr-main-025` | failed | failed | completed | 4/4 | 1 |
| `dr-main-029` | failed | not tested | completed | 5/5 | 0 |

Across these four release-candidate runs:

```yaml
run_count: 4
completed_count: 4
completion_rate: 1.0
total_tokens: 2678037
mean_total_tokens: 669509.25
mean_latency_ms: 157243.50
total_search_calls: 22
total_fetch_calls: 17
recovery_researcher_runs: 3
```

This evidence validates guard behavior and justifies a full regression run. It
does not establish statistical significance or unseen-task generalization.

## Official v2 Regression Run

- Run all 30 cases in `research_main_v1.jsonl` exactly once.
- Use an explicit run date and a 900-second per-case timeout.
- Preserve every completed, agent-failure, infrastructure-failure, and timeout
  result; do not replace undesirable outcomes.
- Publish v2 results separately under `evals/results/published/main_v2/`.
- Collect model cost from Langfuse `GENERATION` observations only.
- Compare v2 with v1 by case ID and report status changes, completion rate,
  citation failures, tokens, latency, search/fetch calls, and recovery usage.
- Label the result as a regression comparison on a previously observed
  dataset, not a holdout benchmark.

## Cost and Stop Gates

The official run retains the v1 safety ceilings:

```yaml
model_spend_cap_usd: 1.50
search_call_cap: 360
```

Before launching the first batch, confirm Langfuse authentication, OpenAI
credit, and Bocha quota. Stop launching new cases if either cap is reached;
record any already-started case normally.

## Change Policy

- The v2.1.0 tag, code, prompts, dataset, runtime settings, and scoring rules
  must not change during the 30-case run.
- A behavior or scoring change requires a new protocol version and new result
  directory.
- Documentation-only corrections that do not change meaning increment the
  patch version.
- Raw v1 and v2 runs are append-only and must never be overwritten.
- Claims about unseen-task performance require a new holdout dataset.

## Freeze Checklist

- [x] P1 evidence inventory and final citation allowlist are implemented.
- [x] P2 structured target plan and bounded recovery are implemented.
- [x] Full Ruff and unit test suite pass (`76 passed`).
- [x] Smoke and main datasets pass deterministic validation.
- [x] Four-case release-candidate validation completes `4/4`.
- [x] The known P1 failure `dr-main-025` completes under P2.
- [x] Runtime configuration and dataset hashes are recorded.
- [x] Interpretation limits are documented.

Release condition: commit these frozen files and create tag
`deep-research-eval-v2.1.0` before launching the official 30-case run.
