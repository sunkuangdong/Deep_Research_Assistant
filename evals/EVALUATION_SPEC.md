# Deep Research Assistant Evaluation Protocol

- **Status:** DRAFT
- **Version:** 1.0.0
- **Protocol Owner:** Kuangdong Sun
- **Dataset Version:** v1
- **Last Updated:** 2026-10-14

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
- Search and delegation budget compliance
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
5. Search, analyst, and editor call limits are not exceeded.
6. The final report contains every case-specific required section.
7. The final report meets the case-specific minimum citation count.

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
- Analyst-call count
- Editor-call count
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
concurrency: 1
search_call_limit: 6
analyst_call_limit: 1
editor_call_limit: 1
```

The following values must be captured in the frozen protocol and every live
result set:

```yaml
provider: <record before freeze>
model_name: <record before freeze>
model_base_url: <record without credentials>
model_max_input_tokens: <record before freeze>
timeout_seconds: <record after smoke runs>
max_provider_retries: 2
```

Secrets, API keys, and credentials must never be written to evaluation files.

## Cost Gate

Before the main benchmark, run two smoke cases and record the average token
usage, API cost, latency, and search calls. Estimate the full-run cost as:

```text
estimated cost = average smoke-run cost * 50 * 1.2
```

The main benchmark must not start until the cost estimate is reviewed and an
explicit spending cap is recorded in the frozen protocol.

## Retry and Failure Policy

- Provider rate limits, network timeouts, and provider 5xx errors may be
  retried at most twice.
- A provider failure that remains after retries is recorded as
  `infrastructure_failure`.
- Agent workflow errors, incomplete artifacts, invalid paths, and budget
  violations are recorded as `agent_failure` and are not retried.
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

- [ ] All main cases and labels have been reviewed.
- [ ] Smoke and main datasets are separate.
- [ ] No required field contains a placeholder.
- [ ] Completion and failure definitions are executable and unambiguous.
- [ ] Provider, model, timeout, retry, and budget values are recorded.
- [ ] The two-case smoke cost estimate and spending cap are recorded.
- [ ] Dataset SHA-256 checksums are generated.
- [ ] The protocol and datasets are committed and tagged.

