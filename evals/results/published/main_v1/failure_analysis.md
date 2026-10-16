# Deep Research Main Benchmark Failure Analysis

- Source bundle: `main_v1`
- Runs: 30
- Completed: 11
- Failed: 19
- Completion rate: 36.67%

## Failure Dimensions

Failure dimensions overlap; counts must not be summed as unique failures.

| Dimension | Cases | Case IDs |
| --- | ---: | --- |
| citation_shortfall | 13 | dr-main-001, dr-main-006, dr-main-009, dr-main-011, dr-main-012, dr-main-013, dr-main-014, dr-main-017, dr-main-019, dr-main-020, dr-main-028, dr-main-029, dr-main-030 |
| source_not_retrieved | 4 | dr-main-014, dr-main-018, dr-main-021, dr-main-027 |
| evidence_provenance | 3 | dr-main-015, dr-main-025, dr-main-027 |
| workflow_incomplete | 1 | dr-main-004 |

## Completion by Category

| Category | Completed | Rate |
| --- | ---: | ---: |
| architecture | 3/5 | 60.00% |
| comparison | 3/5 | 60.00% |
| cost | 1/5 | 20.00% |
| deployment | 3/5 | 60.00% |
| governance | 1/5 | 20.00% |
| security | 0/5 | 0.00% |

## Completion by Language

| Language | Completed | Rate |
| --- | ---: | ---: |
| en | 4/15 | 26.67% |
| zh | 7/15 | 46.67% |

## Prioritized Code Changes

### P1: Add a structured evidence inventory and block drafting until it is valid

- Potential coverage: 18/19 observed failures (94.74%)
- Cases: dr-main-001, dr-main-006, dr-main-009, dr-main-011, dr-main-012, dr-main-013, dr-main-014, dr-main-015, dr-main-017, dr-main-018, dr-main-019, dr-main-020, dr-main-021, dr-main-025, dr-main-027, dr-main-028, dr-main-029, dr-main-030
- Target files: `src/workflow/deepagents_runner.py`, `src/workflow/delegation_guard.py`, `src/tools/lib/prompts.py`, `src/workflow/evidence_inventory.py (new)`
- Implementation:
  - Record canonical URLs returned by web_search and successful web_fetch calls in a structured per-run evidence inventory.
  - Before analyst delegation or draft creation, verify that the inventory contains at least the case-specific minimum number of distinct source pages.
  - Allow the final report to cite only inventory entries that are also present in findings or analysis.
  - Return an actionable deficit to the agent while recovery budget remains instead of discovering the violation after the run.
- Validation:
  - Unit-test URL canonicalization, duplicate pages, provenance checks, and citation deficits.
  - Run the frozen failure cases as a v2 regression set; do not replace v1 results.

### P2: Reserve research capacity for citation recovery and assign distinct source targets

- Potential coverage: 13/19 observed failures (68.42%)
- Cases: dr-main-001, dr-main-006, dr-main-009, dr-main-011, dr-main-012, dr-main-013, dr-main-014, dr-main-017, dr-main-019, dr-main-020, dr-main-028, dr-main-029, dr-main-030
- Target files: `src/workflow/deepagents_runner.py`, `src/tools/lib/prompts.py`
- Implementation:
  - Require the research plan to allocate enough distinct source-page targets to satisfy the citation threshold before delegation starts.
  - Reserve one bounded recovery opportunity until the evidence inventory passes, instead of exhausting all search and researcher calls during initial exploration.
  - Make each researcher report the exact distinct URLs it preserved so the orchestrator can choose a non-duplicate recovery target.
- Validation:
  - Assert that a five-citation case cannot enter drafting with fewer than five eligible evidence URLs.
  - Measure completion, search calls, latency, and token usage on the citation-shortfall regression subset.

### P3: Generate final citations from an allowlist of canonical evidence URLs

- Potential coverage: 6/19 observed failures (31.58%)
- Cases: dr-main-014, dr-main-015, dr-main-018, dr-main-021, dr-main-025, dr-main-027
- Target files: `src/workflow/evidence_inventory.py (new)`, `src/tools/lib/prompts.py`, `evals/scoring.py`
- Implementation:
  - Normalize harmless URL variants consistently while preserving the exact fetched or searched URL for audit evidence.
  - Expose the eligible citation allowlist to the editor and finalization stage.
  - Reject invented paths, altered documentation URLs, and citations introduced only during drafting or editing.
- Validation:
  - Add regression fixtures for path-versus-dot URL variants, fragments, redirects, and query strings.
  - Verify zero citations_not_retrieved and zero citations_without_evidence on the affected cases.

### P4: Enforce draft, editor, and final-report completion with explicit phase state

- Potential coverage: 1/19 observed failures (5.26%)
- Cases: dr-main-004
- Target files: `src/workflow/deepagents_runner.py`, `src/workflow/delegation_guard.py`
- Implementation:
  - Track workflow phases explicitly rather than relying only on prompt instructions.
  - If research and analysis are complete but the agent attempts to stop, resume only the missing draft, review, or finalization phase within the existing limits.
  - Persist the terminal phase and reason in run metadata for auditability.
- Validation:
  - Simulate an agent stopping after analysis and assert that finalization resumes once without looping.
  - Keep the existing timeout, editor, and draft-edit limits enforced.

## Interpretation Guardrail

Potential coverage counts identify observed failure conditions targeted by a change. They are not predicted pass counts and require a new versioned evaluation.
