# Evaluation

This directory contains the evaluation protocol, datasets, and immutable
result artifacts for Deep Research Assistant.

## Current Status

The protocol is currently **DRAFT**. No benchmark result is official until the
freeze checklist in [`EVALUATION_SPEC.md`](./EVALUATION_SPEC.md) is complete.

## Files

```text
evals/
├── EVALUATION_SPEC.md
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

The deterministic acceptance checks cover:

- required artifacts, paths, report sections, and citation count;
- output-language compliance for artifacts, todos, and the final reply;
- search, researcher, analyst, editor, and draft-edit call limits;
- citation URL syntax, provenance in findings/analysis, and confirmation that
  the URL was returned by the configured search provider during the same run.
- exact report-filename agreement with the explicitly captured run date.

The source check intentionally does not issue a second HTTP request for every
URL. Transient 403, rate-limit, and timeout responses would make completion
non-deterministic; in-run search retrieval is recorded as the reproducible
evidence boundary instead.

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

The remaining freeze steps are to review the labels, record the two-case cost
estimate and spending cap, then commit and tag protocol v1.

No file in this directory contains API credentials.

