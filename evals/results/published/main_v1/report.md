# Published Deep Research Main Benchmark

- Protocol: `1.3.0`
- Model: `gpt-6-luna`
- Dataset SHA-256: `9595213afcdd0b7baedf00f948d8364560e7484378ad06f88c0ed44d356fbf42`
- Scorer SHA-256: `719d828f5a94d54f0fdf240bca6e8e2ca4004b6459e4d627a570804e7703336e`
- Completion: 11/30
- Model cost: $0.588057 across 30 main benchmark runs

| Case | Status | Latency (ms) | Total tokens | Citations | Status changed by rescore |
| --- | --- | ---: | ---: | ---: | --- |
| dr-main-001 | agent_failure | 143524 | 633590 | 4 | no |
| dr-main-002 | completed | 125761 | 647194 | 6 | no |
| dr-main-003 | completed | 108617 | 821834 | 6 | no |
| dr-main-004 | agent_failure | 115974 | 468463 | 0 | no |
| dr-main-005 | completed | 106822 | 603714 | 6 | no |
| dr-main-006 | agent_failure | 129705 | 704940 | 4 | no |
| dr-main-007 | completed | 103751 | 696342 | 5 | no |
| dr-main-008 | completed | 158750 | 742977 | 6 | no |
| dr-main-009 | agent_failure | 108176 | 689832 | 4 | no |
| dr-main-010 | completed | 123621 | 648753 | 5 | no |
| dr-main-011 | agent_failure | 145163 | 685380 | 4 | no |
| dr-main-012 | agent_failure | 187539 | 688144 | 4 | no |
| dr-main-013 | agent_failure | 191618 | 901921 | 3 | no |
| dr-main-014 | agent_failure | 220033 | 674656 | 4 | no |
| dr-main-015 | agent_failure | 155184 | 572275 | 4 | no |
| dr-main-016 | completed | 486620 | 1989968 | 5 | no |
| dr-main-017 | agent_failure | 250178 | 1283379 | 3 | no |
| dr-main-018 | agent_failure | 158777 | 720037 | 6 | no |
| dr-main-019 | agent_failure | 145894 | 597568 | 4 | no |
| dr-main-020 | agent_failure | 162249 | 621436 | 4 | no |
| dr-main-021 | agent_failure | 85714 | 458047 | 8 | no |
| dr-main-022 | completed | 156532 | 923860 | 5 | no |
| dr-main-023 | completed | 122738 | 517276 | 4 | no |
| dr-main-024 | completed | 152533 | 654789 | 5 | no |
| dr-main-025 | agent_failure | 87948 | 599712 | 4 | no |
| dr-main-026 | completed | 155182 | 737313 | 5 | no |
| dr-main-027 | agent_failure | 133281 | 682044 | 6 | no |
| dr-main-028 | agent_failure | 194050 | 829598 | 3 | no |
| dr-main-029 | agent_failure | 125198 | 589558 | 2 | no |
| dr-main-030 | agent_failure | 104439 | 477157 | 3 | no |

## Aggregate Metrics

- Completion rate: 36.67%
- Artifact completeness rate: 98.89%
- Language compliance rate: 100.00%
- Budget compliance rate: 100.00%
- Source-link compliance rate: 80.00%
- Median total tokens: 678350.0
- P95 total tokens: 1283379
- Median latency: 144343.5 ms
- P95 latency: 250178 ms

<!-- cost-evidence:start -->
## Cost Evidence

- Langfuse model cost: $0.588057 total; $0.019602 mean per run.
- Projected model cost for 50 runs: $0.980096; $1.176115 with the 120% multiplier.
- Model spend cap: $1.50; within cap: true.
- Bocha main benchmark usage: 178 calls, allocated cost CNY 0.6408.
- Projected Bocha usage: 356 calls with buffer; cap 360 calls.
- Root observations are excluded; model cost is summed only from priced `GENERATION` observations.
- Full trace-level evidence is stored in `costs.json`.
<!-- cost-evidence:end -->

## Audit Notes

- Source `raw_runs.jsonl` files were not modified.
- Every selected workspace was rescored with the scorer hash above.
- The latest run per fixed case ID was selected before rescoring.
- Final reports are copied under `reports/`; supporting artifact hashes are in `manifest.json`.
- Main benchmark metrics include every fixed case selected under the frozen protocol.
