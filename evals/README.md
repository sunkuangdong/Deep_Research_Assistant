# Evaluation

This directory contains the evaluation protocol, datasets, and immutable
result artifacts for Deep Research Assistant.

## Current Status

Protocol v1.3.0 is **FROZEN** at Git tag `deep-research-eval-v1.3.0` and remains
the immutable baseline. Protocol v2.1.0 freezes the evidence-inventory and
bounded-recovery regression workflow described in `EVALUATION_SPEC_V2.md`.
Its results are official only when executed from tag
`deep-research-eval-v2.1.0` and published separately from v1.

## Files

```text
evals/
├── EVALUATION_SPEC.md
├── EVALUATION_SPEC_V2.md
├── README.md
├── datasets/
│   ├── research_smoke_v1.jsonl
│   └── research_main_v1.jsonl
├── validation.py
├── scoring.py
├── runtime_config.py
├── run_deep_research.py
└── results/
```

The six smoke cases are development inputs only. They are excluded from main
benchmark metrics and may be used to validate the future runner, confirm metric
collection, determine timeouts, and estimate live API cost.

## Local Validation

```bash
source .venv/bin/activate
python -m pip install -r requirements-dev.txt
python -m evals.validation
python -m pytest -p no:cacheprovider tests/test_evaluation.py -q
python -m ruff check --no-cache evals src/tools/lib/model.py src/workflow/deepagents_runner.py tests/test_evaluation.py
```

Run the two-case cost-gate smoke after reviewing the cases:

```bash
python -m evals.run_deep_research \
  --case-id dr-smoke-001 \
  --case-id dr-smoke-006 \
  --run-date 2026-10-14 \
  --timeout-seconds 900
```

The runner creates an isolated workspace per case, records a credential-free
`config.json`, and appends every outcome to `raw_runs.jsonl`. A failed or timed
out case is preserved rather than silently replaced.

DeepAgents graph execution defaults to a 120-step recursion limit. Override it
with `DEEPAGENTS_RECURSION_LIMIT` only before freezing the protocol; every live
result captures the effective value.

Bocha search requests use a 20-second timeout and retry transient transport,
HTTP 429, and HTTP 5xx failures at most twice. Override these defaults with
`BOCHA_TIMEOUT_SECONDS` and `BOCHA_MAX_RETRIES` when necessary.

When search misses a known official page, researchers may use the bounded
`web_fetch` tool to retrieve and verify it directly. The fetcher accepts only
public HTTP(S) text pages, rejects local/private destinations, follows at most
three redirects, and limits each response to 200,000 bytes and 12,000 visible
characters. Its defaults can be adjusted with `WEB_FETCH_TIMEOUT_SECONDS`,
`WEB_FETCH_MAX_RETRIES`, `WEB_FETCH_MAX_BYTES`, and `WEB_FETCH_MAX_CHARS`.
Repeated fetches of the same page, including different `#fragment` anchors,
are rejected without consuming the shared fetch budget and are recorded as
diagnostic attempts.

The deterministic acceptance checks cover:

- required artifacts, paths, report sections, and citation count;
- output-language compliance for artifacts, todos, and the final reply;
- search, direct-fetch, researcher, analyst, editor, and draft-edit call limits;
- citation URL syntax, provenance in findings/analysis, and confirmation that
  the URL was returned by search or successfully fetched during the same run.
- exact report-filename agreement with the explicitly captured run date.

The source check intentionally does not issue a second HTTP request for URLs
already returned by search. Direct-fetch URLs count only when their bounded
retrieval succeeds and the final URL is recorded in the run metadata.

## Optional Langfuse Tracing

Langfuse tracing is opt-in and does not replace the local JSONL evidence. When
enabled, every evaluation case becomes one trace containing the nested
DeepAgents, model, and tool observations. The local deterministic scores are
also attached to that trace.

Add project-scoped credentials to `.env`:

```dotenv
LANGFUSE_PUBLIC_KEY=pk-lf-...
LANGFUSE_SECRET_KEY=sk-lf-...
LANGFUSE_BASE_URL=https://us.cloud.langfuse.com
LANGFUSE_TRACING_ENABLED=true
LANGFUSE_TRACING_ENVIRONMENT=evaluation
LANGFUSE_SAMPLE_RATE=1
```

Check authentication before a paid smoke run:

```bash
python -c "from dotenv import load_dotenv; load_dotenv(); from langfuse import get_client; print(get_client().auth_check())"
```

If tracing is enabled but the package or credentials are missing, the runner
fails before making a model call. If tracing is disabled, the existing runner
behavior is unchanged. Trace IDs are written to `raw_runs.jsonl`, and queued
events are flushed once after the full run set.

The frozen protocol uses a USD 1.50 model-cost cap and a 360-call search cap for
the 50-run main-plus-stability plan. Smoke cost evidence is published under
`evals/results/published/smoke_v1/` and excluded from main benchmark metrics.

## Published Cost Collection

After publishing a fixed result bundle, collect exact model costs from the
Langfuse `GENERATION` observations referenced by `rescored_runs.jsonl`:

```bash
python -m evals.collect_costs \
  --published-dir evals/results/published/smoke_v1 \
  --bocha-package-price-cny 3.6 \
  --bocha-package-calls 1000 \
  --bocha-remaining-calls 934 \
  --target-run-count 50 \
  --projection-buffer 1.2 \
  --model-spend-cap-usd 1.50 \
  --search-call-cap 360 \
  --openai-credit-balance-usd 5.82 \
  --balance-snapshot-date 2026-10-15
```

The collector fails before writing if any trace is missing, the Langfuse
generation count differs from the local `llm_calls` metric, or a generation is
unpriced. It sums only `GENERATION` observations, so trace and root-span totals
are not counted twice. The command writes `costs.json` and updates the published
`summary.json` and `report.md`; it never exports Langfuse credentials.

Terminal recursion, timeout, and provider/runtime failures may not return local
workflow metrics. For those failure types only, the collector uses priced
Langfuse `GENERATION` observations for model calls and matching `web_search`
`TOOL` observations for search-call accounting. Missing local metrics and their
trace-derived replacements are listed explicitly in `costs.json`; normal runs
still require an exact local-to-Langfuse generation-count match.

## Published Regression Comparison

After publishing and pricing both main bundles, generate the auditable v1/v2
comparison:

```bash
python -m evals.compare_results \
  --baseline-dir evals/results/published/main_v1 \
  --candidate-dir evals/results/published/main_v2 \
  --output-dir evals/results/published/main_v1_vs_v2
```

The comparison validates dataset, model, case IDs, trace coverage, and pricing
before writing `comparison.json`, `report.md`, and a SHA-256 manifest. It labels
v2 as a regression comparison on a previously observed dataset, not a holdout
benchmark.

No file in this directory contains API credentials.

