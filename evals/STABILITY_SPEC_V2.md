# Deep Research Assistant v2 Stability Protocol

- **Status:** FROZEN
- **Version:** 1.0.0
- **Frozen At:** 2026-10-16
- **Parent Protocol:** `2.1.0`
- **Subset Manifest:** `evals/stability_subset_v1.json`

## Purpose

This protocol measures repeated-run stability for the v2.1.0 Deep Research
workflow. It does not revise the 30-case regression benchmark and does not
estimate performance on unseen tasks.

Each selected task has three observations. The first observation is reused
from `evals/results/published/main_v2`; two additional observations are run
with the same dataset, model, prompt, budgets, timeout, and acceptance checks.

## Selection

The ten-task subset is frozen in `evals/stability_subset_v1.json`. The rule
uses only case ID and dataset labels, never completion status or failure type.
It produces five English and five Chinese tasks, covers all six categories,
and includes eight analysis and two `no_analysis` tasks.

The subset was frozen after the v2 main regression results were observed. The
stability result must therefore be described as post-benchmark descriptive
evidence, not as preregistered or holdout evidence.

## Execution

- Reuse the matching `main_v2` run as `repeat_index=1`.
- Run the frozen ten cases once as `repeat_index=2`.
- Run the same ten cases again as `repeat_index=3`.
- Preserve every outcome, including acceptance, recursion, timeout, and
  provider/runtime failures.
- Do not replace or rerun an undesirable observation.
- Use unique result directories and Langfuse traces for both additional rounds.

## Compatibility Checks

Before publication, the stability publisher verifies:

- the source dataset and subset SHA-256 fingerprints;
- the exact frozen case IDs and recorded strata;
- three observations per task and one observation per round;
- unique Langfuse trace IDs;
- matching protocol, provider, model, temperature, reasoning effort, timeout,
  recursion limit, call budgets, and evidence gates;
- explicit source directories and Git commits for every observation.

The Git commit may differ because evaluation-only publishing tools were added
after the main run. All observed commits are disclosed in the output rather
than silently treated as identical workflow revisions.

## Metrics

The report includes:

- all-three binary completion agreement;
- all-three exact status agreement;
- completed-run count and completion frequency per task;
- token and latency mean, median, range, sample standard deviation, and
  coefficient of variation when enough local measurements exist;
- search, fetch, researcher, analyst, editor, and draft-edit call variation;
- mixed-outcome and missing-metric cases;
- pooled observation counts, reported separately from the 30-case main result.

The 30 observations are clustered within ten tasks and must not be described
as 30 independent benchmark tasks. Structural completion does not establish
factual correctness or citation entailment.
