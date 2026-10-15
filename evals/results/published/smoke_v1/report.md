# Published Deep Research Smoke Evaluation

- Protocol: `1.3.0-draft`
- Model: `gpt-6-luna`
- Dataset SHA-256: `3ccaf7875e499bde0aaaa5f062aa0acafed6e02f00ddde264ed7f4dc5cf10f59`
- Scorer SHA-256: `719d828f5a94d54f0fdf240bca6e8e2ca4004b6459e4d627a570804e7703336e`
- Completion: 6/6
- Model cost: $0.108101 across 6 smoke runs

| Case | Status | Latency (ms) | Total tokens | Citations | Status changed by rescore |
| --- | --- | ---: | ---: | ---: | --- |
| dr-smoke-001 | completed | 157642 | 696312 | 5 | yes |
| dr-smoke-002 | completed | 180224 | 577373 | 5 | no |
| dr-smoke-003 | completed | 113410 | 589993 | 6 | no |
| dr-smoke-004 | completed | 257578 | 729842 | 4 | no |
| dr-smoke-005 | completed | 156980 | 505929 | 6 | no |
| dr-smoke-006 | completed | 147773 | 378174 | 3 | no |

## Aggregate Metrics

- Completion rate: 100.00%
- Artifact completeness rate: 100.00%
- Language compliance rate: 100.00%
- Budget compliance rate: 100.00%
- Source-link compliance rate: 100.00%
- Median total tokens: 583683.0
- P95 total tokens: 729842
- Median latency: 157311.0 ms
- P95 latency: 257578 ms

<!-- cost-evidence:start -->
## Cost Evidence

- Langfuse model cost: $0.108101 total; $0.018017 mean per run.
- Projected model cost for 50 runs: $0.900842; $1.081011 with the 120% multiplier.
- Model spend cap: $1.50; within cap: true.
- Bocha smoke usage: 32 calls, allocated cost CNY 0.1152.
- Projected Bocha usage: 320 calls with buffer; cap 360 calls.
- Root observations are excluded; model cost is summed only from priced `GENERATION` observations.
- Full trace-level evidence is stored in `costs.json`.
<!-- cost-evidence:end -->

## Audit Notes

- Source `raw_runs.jsonl` files were not modified.
- Every selected workspace was rescored with the scorer hash above.
- The latest run per fixed case ID was selected before rescoring.
- Final reports are copied under `reports/`; supporting artifact hashes are in `manifest.json`.
- Smoke metrics validate the harness and are excluded from the main benchmark.
