# Deep Research v2 Pre-Freeze Validation

- Protocol candidate: `2.1.0-rc`
- Run date: `2026-10-16`
- Model: `gpt-6-luna`
- Cases: `dr-main-001`, `dr-main-014`, `dr-main-025`, `dr-main-029`
- Completed: `4/4`

## Result

All four cases completed with exact citation minimums, valid evidence
provenance, in-run retrieval confirmation, complete artifacts, correct output
language, and compliant execution budgets.

Three runs used the reserved evidence-recovery researcher. `dr-main-029`
reached five eligible pages with the two initial researchers and correctly left
the recovery slot unused. `dr-main-025`, the known P1 failure, improved from a
three-of-four eligible-page deficit with no draft/report to a complete report
with four-of-four eligible pages.

## Aggregate Metrics

| Metric | Value |
| --- | ---: |
| Completion | 4/4 (100%) |
| Total tokens | 2,678,037 |
| Mean tokens | 669,509.25 |
| Mean latency | 157.24 seconds |
| Search calls | 22 |
| Fetch calls | 17 |
| Runs using recovery researcher | 3 |

## Source Runs

| Case | Result directory | Trace ID |
| --- | --- | --- |
| `dr-main-001` | `20261016T174331Z_gpt-6-luna_research_main_v1` | `08ca55251a7caa76b1e76b08f7a720aa` |
| `dr-main-014` | `20261016T174331Z_gpt-6-luna_research_main_v1` | `f7425dcbf6568dda396e0c239432fcc1` |
| `dr-main-029` | `20261016T174331Z_gpt-6-luna_research_main_v1` | `fbd28a6b155479d055110e781ba43d52` |
| `dr-main-025` | `20261016T175732Z_gpt-6-luna_research_main_v1` | `77139bb8b5353e2b385784d5ff3c4c7c` |

## Interpretation

This is a targeted regression validation using known v1 failures. It verifies
that the new controls execute correctly and supports running the full 30-case
regression benchmark. It is not an independent holdout result and must not be
used to claim statistically significant or unseen-task improvement.
