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
│   └── research_smoke_v1.jsonl
└── results/
```

The six smoke cases are development inputs only. They are excluded from main
benchmark metrics and may be used to validate the future runner, confirm metric
collection, determine timeouts, and estimate live API cost.

## Planned Next Steps

1. Review the smoke cases and their case-specific success requirements.
2. Define the 30-case main benchmark without reusing smoke cases.
3. Implement an offline protocol/dataset validator.
4. Implement append-only live result capture.
5. Run two smoke cases and freeze the cost cap and runtime configuration.
6. Freeze and tag protocol v1 before running the main benchmark.

No file in this directory contains API credentials.

