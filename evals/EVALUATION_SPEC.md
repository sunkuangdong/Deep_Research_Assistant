# Deep Research Assistant Evaluation Protocol

- **Status:** FROZEN
- **Version:** 1.3.0
- **Protocol Owner:** Kuangdong Sun
- **Dataset Version:** v1
- **Frozen At:** 2026-10-15
- **Last Updated:** 2026-10-15

## Objective

This evaluation measures the reliability and efficiency of the current
file-handoff multi-agent research workflow. It is designed to answer four
questions:

1. How often does the workflow produce a complete research report?
2. Does each run respect artifact, path, search, and delegation constraints?
3. How many model calls and tokens does a completed run consume?
4. What are the median and tail latencies of the end-to-end workflow?

The initial protocol evaluates the existing architecture. It does not claim
that file-based context isolation reduces token usage relative to a
non-isolated architecture.

## In Scope

- Six smoke tasks used only to validate the evaluator and estimate API cost
- Thirty fixed main benchmark tasks
- A stratified ten-task repeated-run stability subset
- Workflow completion rate
- Artifact completeness
- Output-language compliance across required artifacts, todos, and final reply
- Citation URL syntax, evidence provenance, and in-run retrieval checks
- Search, direct-fetch, researcher, analyst, editor, and draft-edit budget compliance
- Input, output, and total token usage
- Model-call, search-call, analyst-call, and editor-call counts
- End-to-end latency
- Failure classification

## Out of Scope

- File-handoff versus full-context ablation
- Claims of causal context-token reduction
- LLM-as-Judge scoring
- Comprehensive human evaluation of factual correctness
- Model fine-tuning
- Comparisons with other agent frameworks
- Voice, RAG retrieval, or tool-routing evaluation

## Dataset

The evaluation uses separate development and benchmark datasets:

| Dataset | Size | Purpose | Included in reported benchmark metrics |
| --- | ---: | --- | --- |
| `research_smoke_v1.jsonl` | 6 | Runner validation, debugging, timeout tuning, and cost estimation | No |
| `research_main_v1.jsonl` | 30 | Main benchmark | Yes |
| Stability subset | 10 selected main tasks | Two additional runs per selected task | Reported separately |

Smoke tasks must never be included in the main benchmark summary. Main-task
success criteria and expected artifacts must be defined before live runs
begin. The benchmark dataset must not be exposed to the agent as reference
material or indexed as knowledge.

Frozen dataset fingerprints:

```yaml
research_smoke_v1_sha256: 3ccaf7875e499bde0aaaa5f062aa0acafed6e02f00ddde264ed7f4dc5cf10f59
research_main_v1_sha256: 9595213afcdd0b7baedf00f948d8364560e7484378ad06f88c0ed44d356fbf42
```

## Test Case Schema

Each JSONL case contains:

```json
{
  "id": "dr-smoke-001",
  "language": "en",
  "category": "multi_source",
  "topic": "Research topic passed to the workflow",
  "no_analysis": false,
  "required_artifacts": [
    "question",
    "research_plan",
    "findings",
    "analysis",
    "draft",
    "report"
  ],
  "required_sections": [
    "Background",
    "Key Findings",
    "Evidence and Analysis",
    "Recommendations",
    "Limitations"
  ],
  "minimum_citations": 5
}
```

Artifact requirements are case-specific. A case executed with
`no_analysis=true` does not require an analysis artifact.

## Success Criteria

A task is `completed` only when all of the following are true:

1. The workflow exits without an unhandled application error.
2. The required final report exists.
3. Every artifact required by the test case exists.
4. Artifact paths comply with the configured workspace path and filename
   rules.
5. Search, direct-fetch, researcher, analyst, editor, and draft-edit call limits are not exceeded.
6. The final report contains every case-specific required section.
7. The final report meets the case-specific minimum citation count.
8. Required artifacts, todos, and the final reply follow the case language.
9. Every report citation is a valid HTTP(S) URL, appears in findings or analysis,
   and was returned by a successful search or successfully fetched from a
   public HTTP(S) page during the same run.
10. The final report filename ends with the explicitly recorded run date.

A task that violates any condition is not completed, even if it returns a
natural-language final response.

## Metrics

### Primary Metrics

- **Completion Rate:** completed valid tasks / all valid tasks
- **Artifact Completeness Rate:** present required artifacts / all required
  artifacts
- **Budget Compliance Rate:** tasks that respect all configured budgets / all
  valid tasks
- **Median and P95 Total Tokens:** calculated from per-run model usage metadata
- **Median and P95 End-to-End Latency:** measured from workflow start to final
  termination

### Diagnostic Metrics

- Input tokens
- Output tokens
- Model-call count
- Search-call count
- Direct-fetch call count
- Direct-fetch attempt, duplicate-rejection, and budget-rejection counts
- Researcher-call count
- Analyst-call count
- Editor-call count
- Draft-edit call count
- Delegation and draft-edit attempt count
- Guardrail rejection count
- Language-violation paths
- Citations missing evidence provenance or in-run retrieval evidence
- Failure type and failed stage

### Stability Metrics

The first run of each stability task is reused from the main benchmark. The
ten selected tasks receive two additional runs, for 50 total live runs:

```text
30 main runs + (10 stability tasks * 2 additional runs) = 50 runs
```

The stability report includes:

- Three-run completion agreement
- Per-task token variation
- Per-task latency variation
- Search and delegation count variation

The main benchmark is a descriptive 30-task result. It must not be described
as a guarantee or as statistically significant.

## Runtime Configuration

The following values are fixed by the current implementation or protocol:

```yaml
temperature: 0
reasoning_effort: none
concurrency: 1
deepagents_recursion_limit: 120
search_call_limit: 6
search_timeout_seconds: 20
search_max_retries: 2
fetch_call_limit: 6
fetch_timeout_seconds: 20
fetch_max_retries: 1
fetch_max_bytes: 200000
fetch_max_chars: 12000
researcher_call_limit: 3
analyst_call_limit: 1
editor_call_limit: 1
draft_edit_call_limit: 1
```

The following provider and execution values are frozen for protocol v1.3.0:

```yaml
provider: openai
model_name: gpt-6-luna
model_base_url: https://api.openai.com/v1
model_max_input_tokens: 131072
timeout_seconds: 900
max_provider_retries: 2
run_date_policy: explicit YYYY-MM-DD value supplied for every live result set
```

Secrets, API keys, and credentials must never be written to evaluation files.

## Cost Gate

Before the main benchmark, run the six development-only smoke cases and record
average token usage, API cost, latency, and search calls. Estimate the full-run
cost as:

```text
estimated cost = average smoke-run cost * 50 * 1.2
```

The frozen smoke evidence and budget gate are:

```yaml
smoke_run_count: 6
mean_total_tokens: 579603.83
median_total_tokens: 583683
mean_latency_ms: 168934.50
median_latency_ms: 157311
mean_model_cost_usd: 0.018016843328
smoke_model_cost_usd: 0.108101059967
mean_search_calls: 5.333333
projected_50_run_model_cost_usd: 0.900842166392
projected_50_run_model_cost_with_20_percent_buffer_usd: 1.081010599670
model_spend_cap_usd: 1.50
projected_50_run_search_calls_with_20_percent_buffer: 320
search_call_cap: 360
```

The runner must stop launching new cases when either cumulative model cost
reaches USD 1.50 or executed search calls reach 360. Any already-started case
must still be recorded. Langfuse priced `GENERATION` observations are the model
cost source of truth; dashboard screenshots are capacity checks only. The
trace-level evidence is stored in
`evals/results/published/smoke_v1/costs.json`.

## Retry and Failure Policy

- Model, search-provider, or direct-fetch rate limits, network timeouts, and provider 5xx
  errors may be retried at most twice.
- A provider failure that remains after retries is recorded as
  `infrastructure_failure`.
- Agent workflow errors, incomplete artifacts, invalid paths, and budget
  violations are recorded as `agent_failure` and are not retried.
- A `GraphRecursionError` is recorded as `agent_failure` with failure type
  `recursion_limit`; it is not classified as a provider outage.
- Budget call counts represent operations that reached their handlers. Attempts
  blocked by hard guardrails are recorded separately as rejection diagnostics
  and do not inflate executed-call counts.
- Direct fetches are deduplicated by scheme, host, path, and query. URL fragments
  identify sections of the same page and do not create additional sources.
- A run must not be replaced because its content or metrics are undesirable.
- Infrastructure failures and agent failures are reported separately.

## Reporting

Each official run set is stored under a unique directory:

```text
evals/results/<date>_<model>_<dataset>/
├── config.json
├── raw_runs.jsonl
├── summary.json
└── report.md
```

Raw results are append-only. The summary and Markdown report must be generated
from `raw_runs.jsonl`. Every result set records:

- Protocol version
- Dataset version and SHA-256 checksum
- Git commit
- Provider and model name
- Run date
- Runtime configuration

## Limitations

- This protocol does not include a non-isolated baseline and cannot establish
  that file handoffs reduce token usage.
- Prompts, web results, and hosted models can change over time, so live results
  may not be perfectly reproducible.
- Structural completion and citation counts do not establish factual
  correctness or citation support quality.
- In-run retrieval proves that a URL was returned by the configured search
  provider or that a bounded direct fetch succeeded; it does not prove that
  every claim is entailed by that page. Search-returned URLs are not fetched a
  second time because transient 403, rate-limit, and timeout responses would
  make the benchmark non-deterministic.
- The 30-task benchmark is a portfolio-scale descriptive evaluation, not a
  production service-level guarantee.

## Change Policy

- Documentation-only corrections that do not change meaning increment the
  patch version.
- Changes to labels, scoring, or individual cases increment the minor version
  and require affected results to be rerun.
- Changes to scope, success criteria, dataset design, model, or core prompt
  require a new major benchmark version.
- Previous protocols, datasets, and raw results must be preserved.
- Prompt changes made after reviewing benchmark failures require a new holdout
  dataset or benchmark version; previous results cannot be overwritten.

## Freeze Checklist

The status may change from `DRAFT` to `FROZEN` only when:

- [x] All main cases and labels have been reviewed.
- [x] Smoke and main datasets are separate.
- [x] No required field contains a placeholder.
- [x] Completion and failure definitions are executable and unambiguous.
- [x] Provider, model, timeout, retry, and budget values are recorded.
- [x] The six-case smoke cost estimate and spending caps are recorded.
- [x] Dataset SHA-256 checksums are generated.
- [x] The protocol and datasets are committed and tagged as
  `deep-research-eval-v1.3.0`.

