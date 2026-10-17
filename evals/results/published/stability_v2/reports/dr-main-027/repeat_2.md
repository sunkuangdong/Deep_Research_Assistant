## Background

Tool-selection evaluation is a multiclass classification problem when each example has one correct tool choice, but real tool inventories are often uneven: common tools may dominate examples while specialized tools appear rarely. Aggregate accuracy can therefore look strong while rare-tool performance remains poor. Evaluation should also distinguish selecting the right tool from producing valid arguments and from successful, safe execution.

This report synthesizes benchmark-design evidence from BFCL and ToolBench, metric definitions from scikit-learn, and official function-calling guidance from OpenAI. The evidence supports a layered evaluation protocol, but does not establish that any one benchmark or metric bundle is empirically optimal.

## Key Findings

1. **Design the dataset to expose imbalance rather than hide it.** Record the candidate-tool inventory, examples and support per tool/category, task type, benchmark version, and split policy. Broad API coverage is not the same as balanced or adequate per-class coverage. BFCL’s versioned release and category-specific cases support reproducible, task-aware evaluation; ToolBench’s broad API inventory and single-/multi-tool tasks are relevant to heterogeneous candidate spaces. Neither source, as captured here, establishes class-frequency balance or stratified splits.
2. **Use Macro F1 as a class-balanced summary, not as the only score.** Macro F1 averages class-level F1 scores equally, so frequent classes do not dominate the aggregate. Pair it with per-class precision, recall, and support: low precision indicates a tool is over-selected, while low recall indicates missed opportunities to select it. State label coverage and zero-division conventions.
3. **Separate tool choice from argument quality.** Schema constraints can check argument structure, but schema conformance does not prove semantic correctness, authorization, or safety. Report tool-choice correctness separately from schema validity and application-level checks.
4. **Use confusion analysis to identify substitutions.** A confusion matrix shows which true tool classes are predicted as which alternatives. Report label order and whether values are raw counts or normalized; for large inventories, pair focused confusion views with per-class summaries.

## Evidence and Analysis

### Dataset design and coverage

A useful evaluation set should represent the actual decision problem: the candidate tools available to the agent, the task categories, and whether a task requires one tool or a sequence/multiple tools. Preserve a held-out test set and identify the benchmark version and split policy. Report both the distribution of examples by correct tool and the candidate-tool inventory; otherwise, a tool may be absent from the test set or represented too sparsely for meaningful class-level conclusions.

BFCL’s maintainer announcement describes a stable v1.0 dataset and evaluation pipeline, a test dataset, and category-specific cases including parallel and parallel-multiple cases. ToolBench describes a broad API space and single- and multi-tool tasks. These are complementary design signals: versioned category coverage helps control evaluation scope, while broad API coverage better reflects heterogeneous tool choice. Neither source establishes that its classes are balanced. The ToolBench scale figures in the captured evidence come from the repository search result; the fetched repository page itself exposed limited content, so those details should be treated with that evidence limitation in mind.

### Metrics for imbalanced classes

For each tool class, precision measures the fraction of predictions for that tool that are correct; recall measures the fraction of examples whose correct tool is that tool that the system identifies. F1 is the harmonic mean of precision and recall. Macro F1 computes class-level F1 and averages classes without weighting by support, making it useful when rare tools matter. A support-weighted score can describe performance under the observed class mix, but it can obscure weak rare classes.

Recommended reporting bundle:

- Macro F1 as the primary class-balanced summary.
- Per-class precision, recall, F1, and support, including classes with zero or very low support.
- Optionally, micro/weighted metrics or overall accuracy as context, clearly labeled as aggregate measures rather than substitutes for class-level reporting.
- The label set/order, averaging convention, and handling of undefined or zero-division cases.

Macro F1 itself can still conceal a particularly weak class. Per-class results are necessary to identify that failure, and support is necessary to interpret how stable the estimate may be. No per-class predictions or counts were available in the evidence reviewed, so no numerical score calculation or empirical comparison is possible here.

### Argument validation and execution outcomes

Evaluate the call in stages: (1) was the correct tool selected; (2) did the arguments conform to the declared schema; (3) were the arguments semantically appropriate and authorized; and (4) did execution produce the intended outcome without unacceptable side effects? OpenAI’s function-calling documentation describes structured tool-call arguments and strict schema constraints, while leaving execution to the application. This supports validating at the application boundary. Schema validity is a structural check, not a guarantee of correct intent, permissions, or safe execution.

Report these outcomes separately as a proposed evaluation design. The cited documentation supports schema constraints and application-side execution responsibility; it does not prescribe or empirically validate this particular multi-stage scoring framework. A combined “successful tool call” score can be useful operationally, but without stage-level results it cannot distinguish a selection error from malformed arguments or an application-side rejection.

### Confusion analysis

Use a confusion matrix with true tool classes as rows and predicted classes as columns. Off-diagonal cells reveal systematic substitutions that a single aggregate score cannot show. Raw counts communicate error volume; row-normalized values help compare error rates across classes with different support. State which representation is shown and preserve the label mapping. For a large tool inventory, provide a full matrix as an artifact where practical and highlight the most consequential or frequent confusions in the report.

### Comparative assessment

The strongest evaluation is layered rather than metric-only: dataset coverage and class support establish what was tested; Macro F1 summarizes class-balanced performance; per-class metrics expose weak tools; confusion analysis diagnoses substitutions; and argument/execution checks separate downstream call quality from selection. This combination is more informative than accuracy or a single benchmark score, but its reliability still depends on representative examples, adequate rare-class support, and a clearly defined ground-truth tool choice.

## Recommendations

1. **Define the label and decision unit.** Specify whether each example has one correct tool, multiple acceptable tools, a no-tool option, or a multi-step sequence. If multiple tools are valid, define the scoring rule before evaluation rather than forcing a single label.
2. **Publish a dataset card/table.** Include benchmark version, candidate tools, task categories, per-tool example support, split policy, and single-/multi-tool coverage. Audit for missing and very low-support classes; do not infer balance from total dataset size.
3. **Report a metric bundle.** Make Macro F1 prominent, alongside per-class precision/recall/F1/support and a clearly labeled aggregate metric such as accuracy or weighted F1. Document label ordering and zero-division handling.
4. **Inspect confusion patterns.** Provide raw and/or row-normalized confusion matrices, explain the normalization, and investigate high-impact substitutions—especially between tools with overlapping functions.
5. **Score call quality in separate stages.** Track tool-choice correctness, schema validity, semantic/domain validity, authorization, and execution outcome independently. Keep application-side validation and side-effect safeguards even when strict schemas are used. This is a recommended evaluation design, not a framework prescribed by the cited documentation.
6. **Use uncertainty-aware interpretation.** Flag classes with sparse support, absent predictions, or undefined metrics. Avoid ranking systems on small differences without adequate per-class evidence or repeated evaluation.

## Limitations

- The reviewed benchmark evidence does not establish actual class imbalance, per-class sampling policy, or stratified splits for BFCL or ToolBench.
- The ToolBench repository page returned limited content in the captured evidence; its scale and task-construction details were surfaced in the search result rather than independently visible in the fetched body.
- No model predictions, per-class supports, benchmark scores, or repeated runs were supplied. This report therefore provides an evaluation design, not an empirical ranking or numerical comparison.
- Metric definitions are grounded in scikit-learn documentation; their application to tool selection is a reasoned mapping, not a claim of empirical optimality.
- The OpenAI documentation supports schema-constrained arguments in the documented function-calling context, but schema conformance does not establish semantic correctness, authorization, safety, or identical behavior across all API modes.
- Confusion matrices can become difficult to inspect for very large tool inventories; the evidence reviewed does not prescribe a single visualization or aggregation method.

## References

- [scikit-learn: `f1_score`](https://scikit-learn.org/stable/modules/generated/sklearn.metrics.f1_score.html)
- [scikit-learn: `confusion_matrix`](https://scikit-learn.org/stable/modules/generated/sklearn.metrics.confusion_matrix.html)
- [Berkeley Function Calling Leaderboard updates (v1.0)](https://github.com/ShishirPatil/gorilla/discussions/583)
- [ToolBench repository README (pinned revision)](https://github.com/OpenBMB/ToolBench/blob/36109f390267075eafa1518dce9ef337ccecedac/README_ZH.md)
- [OpenAI: Function calling](https://developers.openai.com/api/docs/guides/function-calling)

## Source inventory

This report cites five distinct source pages preserved in this run’s findings and confirmed by the evidence inventory as eligible for citation. No additional URLs were introduced during drafting.