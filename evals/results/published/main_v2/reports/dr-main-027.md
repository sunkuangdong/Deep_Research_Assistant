# Evaluating Tool-Selection Quality Under Imbalanced Tool Classes

## Background

An agent that chooses among tools can be evaluated as a classification problem, but a single accuracy score is often inadequate when tool classes have very different frequencies. If common tools dominate the test set, aggregate performance may look strong while the agent rarely selects a less frequent but important tool. Evaluation also needs to distinguish several stages: selecting the right tool, producing usable arguments, executing the call, and recovering from failures.

The [OpenAI function-calling guide](https://developers.openai.com/api/docs/guides/function-calling) describes tool calls as model outputs that an application executes, supporting separate measurement of model selection/arguments and downstream execution. The [Gorilla repository](https://github.com/ShishirPatil/gorilla) is a primary project source for the Berkeley Function-Calling Leaderboard (BFCL), but the retrieved material did not establish its exact rare-tool sampling or split policy.

## Key Findings

1. **Design the test set to expose imbalance and generalization.** Include low-frequency tools, semantically similar alternatives, ambiguous and underspecified requests, no-suitable-tool cases, and abstention. Report per-tool and per-category support. Keep paraphrases, near-duplicates, and examples derived from the same task or schema together when splitting data to reduce leakage. Where relevant, add held-out tools, combinations, or schema variations. These are recommended evaluation practices; the retrieved benchmark source does not verify that BFCL implements each one.

2. **Use Macro F1 alongside prevalence-sensitive metrics.** Macro F1 computes F1 per class and averages classes equally, so rare tools are not overwhelmed by frequent ones. Accuracy or micro/example-weighted metrics answer a different question: performance under the evaluated example distribution. Report both when class parity and deployment-like performance matter, plus per-tool precision, recall, F1, and support. State the class inventory and how undefined or absent-class scores are handled. The [scikit-learn F1 documentation](https://scikit-learn.org/stable/modules/generated/sklearn.metrics.f1_score.html) defines the averaging options and supports per-class reporting.

3. **Validate arguments separately from tool identity.** A correct tool can have malformed or constraint-violating arguments; structurally valid arguments can still belong to the wrong tool or fail to meet user intent. Report schema-valid argument rate among attempted calls and categorize validation failures, separately from selection metrics and end-to-end execution success. The [JSON Schema validation specification](https://json-schema.org/draft/2020-12/json-schema-validation) covers structural assertions such as types, required properties, enums, and bounds. Schema validity is not proof of semantic correctness.

4. **Use confusion analysis to find systematic substitutions.** A fixed-label confusion matrix shows which actual tools are predicted as which alternatives. Report raw counts to retain prevalence context and row-normalized values to compare class-specific error patterns. The [scikit-learn confusion matrix documentation](https://scikit-learn.org/stable/modules/generated/sklearn.metrics.confusion_matrix.html) defines rows as true classes and columns as predicted classes. Pair the matrix with per-class precision and recall; it diagnoses where errors concentrate, not why they occurred.

5. **Keep selection-focused and end-to-end evaluations distinct.** Score tool choice and arguments before execution, using controlled or deterministic backends where possible. Separately measure execution, error handling, and recovery. This avoids attributing backend failures to selection quality while still measuring the complete agent experience.

## Evidence and Analysis

Macro F1 and accuracy are complementary rather than interchangeable. Macro F1 is appropriate when each tool class deserves equal attention or rare-tool capability is a goal. Accuracy and micro/example-weighted summaries are useful for estimating performance under the evaluated prevalence, but can conceal weak rare-class recall or precision. Sparse rare-class support can make Macro F1 unstable, so class counts and per-class results should accompany it.

A practical evaluation should use a layered scorecard:

- **Selection:** accuracy plus Macro F1 and per-tool precision, recall, F1, and support.
- **Confusions:** fixed-label raw and row-normalized confusion matrices.
- **Arguments:** schema-valid rate among attempted calls, with failure categories and schema version.
- **End-to-end behavior:** execution success and recovery, reported separately from selection and argument validity.

For dataset design, retain a deployment-like test distribution if expected operational performance is important, while also ensuring adequate rare-tool coverage or reporting a separate class-balanced diagnostic set. Document sampling and weighting so the two views are not conflated. Include realistic ambiguity and adversarial cases, and use leakage-resistant splits to test generalization rather than memorization.

## Recommendations

1. Define the tool-class inventory and intended evaluation question before sampling. Preserve a deployment-like test set for prevalence-sensitive estimates; add a clearly labeled rare-tool-focused evaluation view when needed.
2. Ensure every relevant tool has test examples, including rare tools and close substitutes. Report support by tool and category; avoid interpreting scores for classes with very small support without uncertainty caveats.
3. Report Macro F1, accuracy or micro/example-weighted performance, and per-tool precision/recall/F1 together. Specify label inclusion and zero-division handling.
4. Publish fixed-label confusion matrices in raw and row-normalized forms. Investigate high-frequency off-diagonal substitutions, especially between tools with overlapping descriptions.
5. Validate arguments against a fixed schema version and report schema-valid rate and failure types separately. Do not treat schema validity as semantic correctness.
6. Score selection and arguments before execution; report execution and recovery as separate end-to-end outcomes.
7. Use leakage-resistant splits and include ambiguity, abstention, no-tool, and adversarial cases. Clearly distinguish verified benchmark properties from recommended protocol design.

## Limitations

The retrieved sources establish metric definitions, schema-validation concepts, and the tool-call interaction model, but do not provide empirical scores, class counts, sample sizes, or confusion matrices. Therefore, no numerical comparison or confidence interval can be calculated. The available BFCL project source did not verify exact rare-tool sampling, split construction, or adversarial coverage. The JSON Schema page is identified in the findings as a June 2022 Internet-Draft marked work in progress; its current normative status should be checked before adopting it as a compliance reference. No single standard aggregate for schema validity or end-to-end success was identified, so denominators and execution conditions should be specified by each evaluation.

**Sources:** [OpenAI API — Function calling](https://developers.openai.com/api/docs/guides/function-calling); [Gorilla repository (BFCL project source)](https://github.com/ShishirPatil/gorilla); [scikit-learn — `f1_score`](https://scikit-learn.org/stable/modules/generated/sklearn.metrics.f1_score.html); [scikit-learn — `confusion_matrix`](https://scikit-learn.org/stable/modules/generated/sklearn.metrics.confusion_matrix.html); [JSON Schema Validation specification](https://json-schema.org/draft/2020-12/json-schema-validation).
