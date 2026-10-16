# Published Deep Research Main Benchmark

- Protocol: `2.1.0`
- Model: `gpt-6-luna`
- Dataset SHA-256: `9595213afcdd0b7baedf00f948d8364560e7484378ad06f88c0ed44d356fbf42`
- Scorer SHA-256: `719d828f5a94d54f0fdf240bca6e8e2ca4004b6459e4d627a570804e7703336e`
- Completion: 24/30
- Model cost: $0.746386 across 30 main benchmark runs

| Case | Status | Latency (ms) | Total tokens | Citations | Status changed by rescore |
| --- | --- | ---: | ---: | ---: | --- |
| dr-main-001 | completed | 265531 | 971221 | 5 | no |
| dr-main-002 | completed | 181335 | 711769 | 5 | no |
| dr-main-003 | agent_failure | 175700 | 572996 | 6 | no |
| dr-main-004 | completed | 210199 | 844250 | 7 | no |
| dr-main-005 | completed | 154968 | 669427 | 5 | no |
| dr-main-006 | completed | 207424 | 679279 | 6 | no |
| dr-main-007 | completed | 213002 | 660480 | 5 | no |
| dr-main-008 | completed | 149123 | 563821 | 5 | no |
| dr-main-009 | completed | 204561 | 795894 | 5 | no |
| dr-main-010 | agent_failure | 369157 | None | n/a | no |
| dr-main-011 | completed | 165409 | 683229 | 5 | no |
| dr-main-012 | agent_failure | 223004 | None | n/a | no |
| dr-main-013 | completed | 173835 | 691502 | 5 | no |
| dr-main-014 | completed | 181474 | 695720 | 5 | no |
| dr-main-015 | completed | 220230 | 916012 | 4 | no |
| dr-main-016 | completed | 205816 | 799673 | 5 | no |
| dr-main-017 | agent_failure | 137794 | 952011 | 0 | no |
| dr-main-018 | completed | 154971 | 606012 | 5 | no |
| dr-main-019 | infrastructure_failure | 900029 | None | n/a | no |
| dr-main-020 | completed | 183982 | 679892 | 5 | no |
| dr-main-021 | completed | 127455 | 480101 | 5 | no |
| dr-main-022 | agent_failure | 226659 | 1309003 | 0 | no |
| dr-main-023 | completed | 111535 | 427479 | 5 | no |
| dr-main-024 | completed | 201066 | 678105 | 6 | no |
| dr-main-025 | completed | 100734 | 404899 | 4 | no |
| dr-main-026 | completed | 216612 | 724536 | 5 | no |
| dr-main-027 | completed | 126047 | 461387 | 5 | no |
| dr-main-028 | completed | 169213 | 793673 | 5 | no |
| dr-main-029 | completed | 121392 | 638211 | 5 | no |
| dr-main-030 | completed | 83198 | 378713 | 4 | no |

## Aggregate Metrics

- Completion rate: 80.00%
- Artifact completeness rate: 86.67%
- Language compliance rate: 86.67%
- Budget compliance rate: 90.00%
- Source-link compliance rate: 90.00%
- Median total tokens: 679892
- P95 total tokens: 971221
- Median latency: 181404.5 ms
- P95 latency: 369157 ms

<!-- cost-evidence:start -->
## Cost Evidence

- Langfuse model cost: $0.746386 total; $0.024880 mean per run.
- Projected model cost for 50 runs: $1.243976; $1.492771 with the 120% multiplier.
- Model spend cap: $1.50; within cap: true.
- Bocha main benchmark usage: 158 calls, allocated cost CNY 0.5688.
- Projected Bocha usage: 317 calls with buffer; cap 360 calls.
- Root observations are excluded; model cost is summed only from priced `GENERATION` observations.
- Full trace-level evidence is stored in `costs.json`.
<!-- cost-evidence:end -->

## Audit Notes

- Source `raw_runs.jsonl` files were not modified.
- Every selected workspace was rescored with the scorer hash above.
- The latest run per fixed case ID was selected before rescoring.
- Final reports are copied under `reports/`; supporting artifact hashes are in `manifest.json`.
- Main benchmark metrics include every fixed case selected under the frozen protocol.
