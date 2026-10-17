# Published Deep Research v2 Stability Evaluation

- Parent protocol: `2.1.0`
- Model: `gpt-6-luna`
- Dataset SHA-256: `9595213afcdd0b7baedf00f948d8364560e7484378ad06f88c0ed44d356fbf42`
- Subset SHA-256: `669f2235e4c861f6808bc74ecdb840ffab40d64a2d1d2f883f8c72bc7d9e2db3`
- Tasks: 10
- Observations: 30
- Model cost: $0.600905 across 30 stability evaluation runs

## Stability Summary

- Three-run completion agreement: 7/10 (70.0%).
- Three-run exact-status agreement: 7/10 (70.0%).
- Mixed completion outcomes: 3 tasks.
- Pooled completion: 23/30 (76.7%); these observations are clustered within ten tasks.

| Case | Completed | Statuses | Completion agreement | Token CV | Latency CV | Search-call range | Researcher-call range |
| --- | ---: | --- | --- | ---: | ---: | ---: | ---: |
| dr-main-003 | 0/3 | agent_failure / agent_failure / agent_failure | yes | 12.5% | 31.6% | 1.0 | 1.0 |
| dr-main-006 | 3/3 | completed / completed / completed | yes | 18.7% | 19.1% | 0.0 | 1.0 |
| dr-main-009 | 3/3 | completed / completed / completed | yes | 11.9% | 24.6% | 1.0 | 1.0 |
| dr-main-012 | 1/3 | agent_failure / completed / agent_failure | no | 13.4% | 11.6% | 1.0 | 1.0 |
| dr-main-015 | 2/3 | completed / completed / agent_failure | no | 37.5% | 47.8% | 1.0 | 1.0 |
| dr-main-018 | 3/3 | completed / completed / completed | yes | 21.6% | 57.2% | 1.0 | 1.0 |
| dr-main-021 | 3/3 | completed / completed / completed | yes | 2.7% | 18.4% | 1.0 | 0.0 |
| dr-main-024 | 2/3 | completed / agent_failure / completed | no | 2.9% | 41.5% | 1.0 | 1.0 |
| dr-main-027 | 3/3 | completed / completed / completed | yes | 31.8% | 51.6% | 1.0 | 1.0 |
| dr-main-028 | 3/3 | completed / completed / completed | yes | 23.2% | 32.0% | 2.0 | 1.0 |

<!-- cost-evidence:start -->
## Cost Evidence

- Langfuse model cost: $0.600905 total; $0.020030 mean per run.
- Projected model cost for 30 runs: $0.600905; $0.600905 with the 100% multiplier.
- Model spend cap: $1.50; within cap: true.
- Bocha stability evaluation usage: 161 calls, allocated cost CNY 0.5796.
- Projected Bocha usage: 161 calls with buffer; cap 360 calls.
- Root observations are excluded; model cost is summed only from priced `GENERATION` observations.
- Full trace-level evidence is stored in `costs.json`.

### Deduplicated Experiment Cost

- Repeat 1 reuses 10 traces already included in `main_v2`; it is not charged a second time in the full experiment total.
- Repeats 2 and 3 add 20 paid runs: $0.391638 and 110 search calls.
- Full v2 experiment: 50 unique paid runs, $1.138024 model cost, and 268 search calls.
- Full-experiment caps: model $1.50 (within cap: true); search 360 calls (within cap: true).
<!-- cost-evidence:end -->

## Audit Notes

- Repeat 1 reuses the immutable published `main_v2` observation.
- Repeats 2 and 3 are rescored from their original workspaces when available.
- Every selected task has exactly three observations and every trace ID is unique.
- The subset was frozen after the main regression run and is not holdout evidence.
- Raw result directories are not modified by publication.
- Structural completion does not establish factual correctness or citation entailment.
