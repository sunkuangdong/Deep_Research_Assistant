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
  --timeout-seconds 900
```

The runner creates an isolated workspace per case, records a credential-free
`config.json`, and appends every outcome to `raw_runs.jsonl`. A failed or timed
out case is preserved rather than silently replaced.

The remaining freeze steps are to review the labels, record the two-case cost
estimate and spending cap, then commit and tag protocol v1.

No file in this directory contains API credentials.

