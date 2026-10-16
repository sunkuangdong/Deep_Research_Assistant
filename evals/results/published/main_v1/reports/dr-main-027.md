# Evaluating Tool-Selection Quality Under Imbalanced Tool Classes

## Background

An agent's tool-selection task can be evaluated as multiclass classification, but ordinary accuracy can be misleading when a few tools dominate the test set. A system may perform well on frequent tools while rarely selecting a useful minority tool. Moreover, selecting the right tool is only one stage of a tool call: arguments can be malformed, semantically wrong, unauthorized, or unsafe even when the tool label is correct. A sound evaluation therefore needs a representative dataset, minority-sensitive metrics, argument checks, and error diagnosis.

## Key Findings

- **Use complementary test distributions.** Preserve a held-out set with realistic tool prevalence for deployment-like estimates, and add a balanced or stratified diagnostic set to expose minority-class weaknesses. Label the purpose of each set; a balanced-set aggregate is not a deployment-prevalence estimate. The APIBench paper describes API coverage and challenges such as argument accuracy and API hallucination, but its accessible abstract does not establish its sampling or split protocol. [Gorilla: Large Language Model Connected with Massive APIs](https://arxiv.org/abs/2305.15334)
- **Macro F1 gives each included tool class equal weight.** It is the unweighted mean of per-class F1 scores, so rare tools matter as much as common ones. Report it with per-tool precision, recall, F1, and support; define the label universe and undefined-score policy. Macro F1 is not a complete measure of deployment utility, calibration, or error cost. [scikit-learn `f1_score`](https://scikit-learn.org/stable/modules/generated/sklearn.metrics.f1_score.html)
- **Separate tool choice from argument and execution quality.** Annotate tool/no-tool decisions, acceptable tools, arguments, and outcomes separately. Validate schema conformance, then independently check semantic constraints, authorization, and safety before execution. The retrieved OpenAI guide was truncated in the findings, and strict-mode details there rely partly on a secondary source; structural conformance should not be treated as semantic correctness. [OpenAI Function calling guide](https://developers.openai.com/api/docs/guides/function-calling)
- **Use confusion analysis to diagnose substitutions.** A confusion matrix can show which true tool classes are predicted as which alternatives; inspect both counts and class-normalized rates, with fixed label order and support. The official scikit-learn documentation defines `C[i, j]` as true class `i` predicted as class `j` and exposes normalization options. [scikit-learn `confusion_matrix`](https://scikit-learn.org/stable/modules/generated/sklearn.metrics.confusion_matrix.html?highlight=confusion_matrix)
- **Design labels and splits to support valid conclusions.** Include no-tool/abstention, ambiguous or multiple acceptable tools, overlapping APIs, invalid arguments, version changes, and sequential calls. Group paraphrases and related examples before splitting; document API/version holdouts to reduce leakage. These are design recommendations, not verified descriptions of APIBench's implementation.

## Evidence and Analysis

### Dataset design

Record per-tool and per-task counts, and ensure minority tools have enough independent examples for meaningful estimates. A natural-prevalence test set answers how the system may perform under a deployment-like mix; a balanced diagnostic set answers whether performance is distributed across classes. Report both distributions and avoid conflating their purposes. Use a hierarchical annotation scheme that distinguishes intent, whether a tool is needed, eligible tools, selected tool, argument validity, and execution outcome. For ambiguous requests, annotate an acceptable set or adjudication rationale rather than forcing an arbitrary single label.

Splits should match the intended generalization claim. Group paraphrases, templates, and examples derived from the same task to avoid near-duplicate leakage. Hold out API identities or families when testing transfer to unseen tools; hold out documentation or versions when testing adaptation to changed APIs. The available APIBench abstract raises documentation adaptation and API hallucination as concerns but does not provide enough detail to infer its actual sampling, labels, or split design.

### Macro F1 and class imbalance

For each class, F1 is the harmonic mean of precision and recall; Macro F1 averages those class-level F1 values without weighting by support. This makes it useful when minority tools deserve equal consideration. It can nevertheless hide large differences among classes, so publish per-tool precision, recall, F1, and support. Fix the label universe across runs and state how undefined scores are handled; absent or extremely sparse classes can make the aggregate sensitive to that policy. Macro F1 is a hard-label summary and does not encode calibration, operational costs, or the relative harm of a wrong tool versus a missed tool.

### Argument validation

Evaluate argument quality as a separate stage from tool identity. Schema checks can test types, required fields, and closed-set values; they do not prove that a value is factually correct, appropriate to the request, authorized, or safe. At the execution boundary, validate the structure and then apply domain-specific invariants, permission checks, and safety controls. Record schema-validity and semantic/authorization failures separately so a correct tool choice with bad arguments is not misclassified as a tool-selection error. The official function-calling page was truncated in the retrieved findings, so detailed claims about current strict-mode behavior should be verified against the full documentation before implementation.

### Confusion analysis

Use a fixed tool-label order and read rows as true classes and columns as predicted classes. Raw counts show volume and support; row-normalized rates show the share of each true class routed correctly or confused with another. Review off-diagonal pairs by both rate and count, then inspect examples to distinguish overlapping tool descriptions, ambiguous labels, missing context, and model routing errors. Slice errors by task family, tool frequency, API/version, argument validity, no-tool/abstention, and single- versus multi-step calls. These slices are diagnostic recommendations; no empirical confusion matrix or observed error pattern was available in the research evidence.

### Integrated evaluation design

A practical scorecard should report (1) natural-prevalence performance, (2) balanced/stratified diagnostic performance, (3) Macro F1 and per-tool metrics with support, (4) confusion matrices in counts and normalized rates, and (5) argument schema, semantic, authorization, and execution outcomes. Keep tool-selection errors distinct from downstream call failures. If operational costs differ, add cost-sensitive measures or task-specific success rates rather than assuming Macro F1 captures utility.

## Recommendations

1. Maintain a deployment-like held-out set and a separate minority-sensitive diagnostic set; publish class counts and sampling/weighting procedures.
2. Define a stable, hierarchical label taxonomy covering tool choice, no-call/abstention, ambiguity or multiple acceptable tools, arguments, and execution outcomes.
3. Prevent leakage by grouping related examples and documenting API identity, family, version, and documentation holdouts.
4. Report Macro F1 alongside per-tool precision, recall, F1, and support; specify the label universe and undefined-score policy.
5. Publish confusion matrices with fixed label order, raw counts, and row-normalized rates; investigate high-impact off-diagonal pairs and relevant slices.
6. Validate arguments before execution in two layers: schema conformance, then semantic, authorization, and safety checks. Track these outcomes separately from tool-selection accuracy.
7. Avoid a single headline score. Add cost-sensitive or task-success measures when tool errors have unequal consequences.

## Limitations

The evidence base is methodological rather than empirical: no tool-selection predictions, class counts, confusion matrix, argument-error rates, or deployment costs were supplied, so no performance estimates or rankings can be made. The APIBench abstract does not establish its class balance, sampling, label schema, or split construction. The scikit-learn pages document metric mechanics, not which metric is optimal for a particular agent. The OpenAI function-calling fetch was truncated in the findings, and some strict-mode detail was supported by a secondary source; verify current official documentation before relying on implementation-specific guarantees. Confusion-analysis slices and dataset recommendations are proposed evaluation practices, not measured findings.

## References

1. [Gorilla: Large Language Model Connected with Massive APIs](https://arxiv.org/abs/2305.15334) — benchmark context and API-use challenges.
2. [f1_score — scikit-learn documentation](https://scikit-learn.org/stable/modules/generated/sklearn.metrics.f1_score.html) — F1 definition, averaging, labels, and undefined-score handling.
3. [Function calling | OpenAI API](https://developers.openai.com/api/docs/guides/function-calling) — tool/function calling and argument schemas; retrieved content was truncated in the findings.
4. [confusion_matrix — scikit-learn documentation](https://scikit-learn.org/stable/modules/generated/sklearn.metrics/confusion_matrix.html?highlight=confusion_matrix) — matrix orientation and normalization options.
5. [OpenAI function-calling strict-mode discussion — Today Toutiao](https://www.toutiao.com/article/7459997148029944332/) — third-party secondary source; not authoritative and should be checked against current official documentation.

## Source note

The report cites five distinct in-run source pages. Four are preserved in the researcher findings; the fifth, the scikit-learn confusion-matrix documentation page, was successfully fetched in this run and is cited here for its directly verified matrix orientation and normalization options. The Today Toutiao page is explicitly treated as a third-party source, not official documentation. Dataset-design and diagnostic recommendations are methodological implications rather than empirical benchmark results; the OpenAI guide fetch was truncated, so implementation-specific strict-mode details require verification against the current official documentation.