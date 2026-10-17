# Final Deep Research Benchmark Report

## Executive Summary

Protocol v2 completed 24/30 regression tasks (80.0%), up from 11/30 (36.7%) in v1. This is a 43.3 percentage-point increase.
On the frozen ten-task stability subset, the system completed 23/30 observations (76.7%) and produced the same completion outcome in all three runs for 7/10 tasks (70.0%).

## Evaluation Design

- Model: `gpt-6-luna`.
- Dataset SHA-256: `9595213afcdd0b7baedf00f948d8364560e7484378ad06f88c0ed44d356fbf42`.
- Main comparison: protocol `1.3.0` versus `2.1.0` on the same 30 tasks.
- The main comparison is regression evidence on a previously observed dataset, not a holdout benchmark.
- Stability evidence consists of ten tasks run three times; the 30 observations are clustered and are not 30 independent tasks.

## Main Regression Results

| Metric | v1 | v2 | Change |
| --- | ---: | ---: | ---: |
| Completion | 11/30 | 24/30 | +43.3 pp |
| Median latency | 144.3s | 181.4s | +25.7% |
| P95 latency | 250.2s | 369.2s | +47.6% |
| Model cost | $0.5881 | $0.7464 | +26.9% |
| Cost per completed case | $0.0535 | $0.0311 | -41.8% |
| Search calls | 178 | 158 | -11.2% |

v2 improved 16 previous failures and regressed 3 previous successes. The higher completion rate came with increased latency and total model cost, while cost per completed case decreased.

## Repeated-Run Stability

- Pooled completion: 23/30 (76.7%).
- Three-run completion agreement: 70.0%.
- Stable completed tasks: dr-main-006, dr-main-009, dr-main-018, dr-main-021, dr-main-027, dr-main-028.
- Stable incomplete tasks: dr-main-003.
- Mixed-outcome tasks: dr-main-012, dr-main-015, dr-main-024.
- Median within-task token CV: 16.1%; median within-task latency CV: 31.8%.

## Cost Accounting

The full v2 plan contained 30 main runs and 20 additional stability runs. After excluding the ten reused main traces, the 50 unique paid runs cost $1.138024 and used 268 search calls.
The two additional stability rounds cost $0.391638. Both the model-spend and search-call caps were respected.

## Failure Analysis

The remaining v2 main failures comprised 3 acceptance-criteria failures, 2 recursion-limit failures, 1 timeout failure.
Repeated runs show that artifact completion and control-flow termination remain variable: three subset tasks had mixed outcomes, and one task failed all three runs at the status level.

## Defensible Claims

- Protocol v2 improved structural completion from 36.7% to 80.0% across the same 30-case regression dataset.
- Model cost per completed case decreased by 41.8%, despite a 26.9% increase in total model cost.
- A frozen ten-task subset achieved 76.7% pooled completion and 70.0% three-run outcome agreement.

## Limitations

- The evidence does not establish that the 80.0% completion rate generalizes to unseen or production tasks.
- The evidence does not establish that the system guarantees factual correctness or citation entailment.
- The evidence does not establish that context isolation reduced token usage without a non-isolated baseline.
- The evidence does not establish that the ten-task stability subset is independent holdout evidence.
- Stability statistics are descriptive because the subset contains only ten tasks and three runs per task.
- Local token metrics were available for 28/30 stability observations; 2 terminal runs were excluded from token-variation statistics.
- Structural completion and source provenance do not independently verify factual correctness.
