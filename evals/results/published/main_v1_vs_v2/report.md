# Deep Research v1 vs v2 Regression Comparison

## Scope and Methodology

This report compares protocol `1.3.0` with `2.1.0` on the same 30 cases, dataset hash `9595213afcdd0b7baedf00f948d8364560e7484378ad06f88c0ed44d356fbf42`, and model `gpt-6-luna`. Because v2 was designed after reviewing v1 failures, this is a regression comparison on a previously observed dataset, not a holdout benchmark.

## Executive Results

| Metric | v1 | v2 | Change |
| --- | ---: | ---: | ---: |
| Completed cases | 11/30 | 24/30 | +13 |
| Completion rate | 36.7% | 80.0% | +43.3 pp |
| Median latency | 144.3s | 181.4s | +25.7% |
| P95 latency | 250.2s | 369.2s | +47.6% |
| Model cost | $0.5881 | $0.7464 | +26.9% |
| Cost per completed case | $0.0535 | $0.0311 | -41.8% |
| Bocha search calls | 178 | 158 | -11.2% |

v2 recovered 16 previous failures, regressed 3 previous successes, kept 8 cases successful, and left 3 cases incomplete.

## Case-Level Transitions

- Improved: dr-main-001, dr-main-004, dr-main-006, dr-main-009, dr-main-011, dr-main-013, dr-main-014, dr-main-015, dr-main-018, dr-main-020, dr-main-021, dr-main-025, dr-main-027, dr-main-028, dr-main-029, dr-main-030
- Regressed: dr-main-003, dr-main-010, dr-main-022
- Stable completed: dr-main-002, dr-main-005, dr-main-007, dr-main-008, dr-main-016, dr-main-023, dr-main-024, dr-main-026
- Stable incomplete: dr-main-012, dr-main-017, dr-main-019

| Case | v1 | v2 | Transition |
| --- | --- | --- | --- |
| dr-main-001 | agent_failure | completed | improved |
| dr-main-002 | completed | completed | stable_completed |
| dr-main-003 | completed | agent_failure | regressed |
| dr-main-004 | agent_failure | completed | improved |
| dr-main-005 | completed | completed | stable_completed |
| dr-main-006 | agent_failure | completed | improved |
| dr-main-007 | completed | completed | stable_completed |
| dr-main-008 | completed | completed | stable_completed |
| dr-main-009 | agent_failure | completed | improved |
| dr-main-010 | completed | agent_failure | regressed |
| dr-main-011 | agent_failure | completed | improved |
| dr-main-012 | agent_failure | agent_failure | stable_not_completed |
| dr-main-013 | agent_failure | completed | improved |
| dr-main-014 | agent_failure | completed | improved |
| dr-main-015 | agent_failure | completed | improved |
| dr-main-016 | completed | completed | stable_completed |
| dr-main-017 | agent_failure | agent_failure | stable_not_completed |
| dr-main-018 | agent_failure | completed | improved |
| dr-main-019 | agent_failure | infrastructure_failure | stable_not_completed |
| dr-main-020 | agent_failure | completed | improved |
| dr-main-021 | agent_failure | completed | improved |
| dr-main-022 | completed | agent_failure | regressed |
| dr-main-023 | completed | completed | stable_completed |
| dr-main-024 | completed | completed | stable_completed |
| dr-main-025 | agent_failure | completed | improved |
| dr-main-026 | completed | completed | stable_completed |
| dr-main-027 | agent_failure | completed | improved |
| dr-main-028 | agent_failure | completed | improved |
| dr-main-029 | agent_failure | completed | improved |
| dr-main-030 | agent_failure | completed | improved |

## Remaining v2 Failures

| Case | Failure type | Deterministic reason |
| --- | --- | --- |
| dr-main-003 | acceptance_criteria | language mismatch |
| dr-main-010 | recursion_limit | recursion limit |
| dr-main-012 | recursion_limit | recursion limit |
| dr-main-017 | acceptance_criteria | incomplete artifacts, insufficient citations (0/5) |
| dr-main-019 | timeout | 900-second timeout |
| dr-main-022 | acceptance_criteria | incomplete artifacts, insufficient citations (0/5) |

## Cost, Latency, and Recovery Trade-offs

Model spend increased by +26.9%, while cost per completed case changed by -41.8%. This efficiency metric allocates the cost of all attempts, including failures, across completed cases.
Median latency changed from 144.3s to 181.4s, and P95 changed from 250.2s to 369.2s. The reliability gain therefore came with a latency trade-off.
Local median token usage was 678350 in v1 and 679892 in v2. This is not a complete token comparison because the sample counts are 30 and 27; Langfuse model-cost totals do cover all 30 traces in both versions.
The v2 recovery Researcher executed in 8 runs (8 calls). Recovery metrics were unavailable for 3 terminal failures whose local workflow metadata was not returned.

## Interpretation

The defensible result is that v2 improved structural completion from 36.7% to 80.0% across the same 30 regression cases while reducing model cost per completed case. It does not establish the same completion rate on unseen tasks or in production.

## Limitations

- The candidate reuses a dataset whose baseline failures were already reviewed; this is a regression comparison, not a holdout benchmark.
- Each task was run once, so the report provides descriptive results without variance estimates or confidence intervals.
- Three candidate terminal failures lack local token metrics; Langfuse costs cover all traces, but local token percentiles use 27 of 30 cases.
- Structural completion and source provenance do not establish factual correctness or full citation entailment.
- This comparison does not include a non-isolated context baseline and cannot establish context-usage reduction.
