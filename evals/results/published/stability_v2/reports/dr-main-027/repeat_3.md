# Evaluating Tool-Selection Quality Under Imbalanced Tool Classes

## Background

An agent’s tool-selection score can look strong when a few common tools dominate the test set, even if the agent rarely routes requests to less frequent tools. Evaluation should therefore distinguish overall performance from class-balanced performance, and should separate choosing the right tool from producing valid arguments and completing the requested operation.

The available benchmark evidence illustrates the scale and complexity of the problem, but not a settled imbalance protocol. ToolBench reports 16,464 real-world APIs across 49 categories and includes single- and multi-tool tasks ([ToolLLM paper](https://arxiv.org/abs/2307.16789)). The available evidence does not establish that its classes are balanced or that results are stratified by class. An official Gorilla/Berkeley Function Calling Leaderboard release is also available, but the reviewed release evidence does not establish its class-frequency distribution or imbalance handling ([BFCL/Gorilla release](https://github.com/ShishirPatil/gorilla/releases/tag/v0.3)).

## Key Findings

- **Design the dataset to expose imbalance.** Define what counts as a class (individual tool, API family, or domain), preserve the candidate-tool set and gold tool label(s) for each example, and publish per-class counts and split composition. Include both single-tool and multi-tool cases where they reflect intended use. A large API inventory alone does not demonstrate balanced coverage.
- **Use Macro F1, but do not report it alone.** Macro F1 gives each evaluated class equal weight, so rare tools matter as much as common ones in the aggregate. Pair it with per-tool precision, recall, F1, and support; retain accuracy or weighted metrics as prevalence-sensitive complements. Scikit-learn documents classification metrics and precision-recall analysis, including their relevance to imbalanced classes ([metrics and scoring](https://scikit-learn.org/stable/modules/model_evaluation.html); [precision-recall example](https://scikit-learn.org/stable/auto_examples/model_selection/plot_precision_recall.html)).
- **Treat argument validity as a separate outcome.** Validate emitted arguments against the selected tool’s schema and report the schema-validation pass rate separately from tool-choice correctness. JSON Schema defines structural assertions such as required properties, types, and value constraints; schema validity does not prove semantic correctness or successful execution ([JSON Schema Validation specification](https://json-schema.org/draft/2020-12/json-schema-validation)).
- **Use confusion analysis to diagnose routing errors.** Report tool-level confusion counts and row-normalized rates. Counts show operational volume; normalization by true class makes minority-class miss-routing easier to compare. Interpret the matrix alongside per-class metrics, not as a replacement for them.
- **Predefine edge-case scoring.** State how abstention/no-tool, malformed outputs, unsupported labels, and multi-tool calls are scored. For multi-tool tasks, specify whether the target is a set, ordered sequence, or acceptable alternatives; a single-label confusion matrix may not represent these cases faithfully.

## Evidence and Analysis

### Dataset design and class imbalance

A benchmark should make the evaluation population auditable. At minimum, record the class unit, candidate tools available for each prompt, gold tool label(s), task type (single or multi-tool), and class support in each split. If the goal is deployment performance, preserve a representative test prevalence and supplement it with class-stratified reporting. If the goal is equal coverage across tools, a balanced or stratified test set can help, but its results should not be presented as deployment-prevalence performance without qualification.

ToolBench’s reported breadth—16,464 APIs across 49 categories—makes it relevant to selection among many APIs, but the reviewed evidence does not provide class-frequency tables, sampling weights, or split rules. Likewise, the reviewed BFCL release does not establish class-level composition. Thus, neither source supports a claim that these benchmarks already solve class imbalance.

### Metrics: Macro F1 and complementary views

For each tool class, calculate precision, recall, and F1, then average class F1 values without weighting by support to obtain Macro F1. This makes Macro F1 useful when rare-tool coverage matters. However, it can be noisy for classes with very few examples, and a single macro score cannot show whether a class’s weakness comes from false positives, false negatives, or both. Always publish per-class support and scores.

Accuracy and support-weighted metrics answer a different question: how well the system performs under the observed class prevalence. They can be useful operational summaries when the test distribution matches deployment, but can conceal poor performance on rare tools. A robust report therefore presents Macro F1 and per-class results alongside accuracy or weighted metrics, rather than choosing one aggregate as the sole measure.

### Argument validation and end-to-end success

Tool selection, argument structure, and task completion are distinct stages. A system may select the correct tool but emit malformed or schema-invalid arguments; it may also produce schema-valid arguments for the wrong tool. Report at least (1) tool-selection metrics, (2) argument schema-validity rate, and, where available, (3) execution or task success. Define the denominator for argument validity—for example, all emitted calls versus calls to the correct tool—and report malformed or missing arguments rather than silently excluding them.

JSON Schema can check structural constraints, including required fields and types. It does not establish that values are appropriate for the user’s intent, safe, or sufficient to complete the task. Those require separate semantic or execution checks.

### Confusion analysis and operational definitions

A confusion matrix can reveal systematic substitutions—for example, a rare tool repeatedly routed to a common neighboring tool. Show raw counts to convey workload and row-normalized rates to compare error rates by true class. For reproducibility, specify the label set and how invalid predictions are represented.

For single-tool tasks, score the selected tool against the gold label and count unparseable or invalid outputs as incorrect (while reporting their frequency), unless a different rule is justified. If no-tool is a valid action, represent it explicitly and distinguish correct abstention from failure to call a required tool. For multi-tool tasks, define whether correctness means an exact set, a partially correct set, or an ordered call chain; report set/sequence-aware measures as appropriate rather than collapsing all cases into a single-label score.

### Trade-offs and suitable use

- **Macro F1 plus per-class metrics** is appropriate when every tool class, including rare ones, matters. Sparse classes require caution and support counts.
- **Accuracy or weighted metrics** are useful for expected performance under a representative deployment distribution, but should not be used alone to claim minority-class competence.
- **Confusion matrices** are diagnostic: counts show volume, normalized rates show class-specific routing weaknesses.
- **Schema-validity rate** measures structural argument conformance, not semantic correctness or task success.
- **Stratified reporting** supports fairer class comparisons; a deployment-representative test set remains important when estimating real-world aggregate performance.

## Recommendations

1. **Specify the task and label space.** Define the class unit, candidate set per example, acceptable tool(s), and whether the task is single-tool, multi-tool, or no-tool.
2. **Publish dataset composition.** Report per-class counts for train/dev/test, sampling and split rules, and any distribution shift. Preserve a deployment-representative test set when operational prevalence matters; add class-stratified results for coverage analysis.
3. **Report a metric bundle.** Include Macro F1, per-tool precision/recall/F1/support, and accuracy or weighted metrics. State how unsupported classes and invalid outputs are handled.
4. **Inspect confusion patterns.** Provide both raw and true-class-normalized confusion matrices, with explicit treatment of abstention and out-of-set predictions.
5. **Validate arguments independently.** Apply each tool’s schema and report the validation denominator and pass rate. Separate schema validity from semantic checks, execution success, and task completion.
6. **Make multi-tool scoring explicit.** Use set- or sequence-aware evaluation where appropriate, and report missing, extra, and misordered calls rather than forcing them into a single-label metric.
7. **Quantify uncertainty for rare classes.** Show support and, where feasible, uncertainty intervals or repeated-sample variability; avoid over-interpreting Macro F1 when some classes have very few examples.

## Limitations

The reviewed sources do not provide class-frequency tables, sampling weights, split rules, prediction-level outputs, confusion counts, or argument-validation results for ToolBench or BFCL. Consequently, no benchmark-specific Macro F1, ranking, or claim of balanced evaluation can be established. The sources support general classification reporting and structural JSON validation, but do not prescribe one canonical tool-selection metric suite or universal rules for abstention and multi-tool calls. Those choices must be declared by evaluators. JSON Schema validation alone cannot establish semantic appropriateness, safety, or successful execution.

**Sources**

- [ToolLLM: Facilitating Large Language Models to Master 16000+ Real-world APIs](https://arxiv.org/abs/2307.16789)
- [Release GoEx and Berkeley Function Calling Leaderboard Updates](https://github.com/ShishirPatil/gorilla/releases/tag/v0.3)
- [scikit-learn: Metrics and scoring](https://scikit-learn.org/stable/modules/model_evaluation.html)
- [scikit-learn: Precision-Recall example](https://scikit-learn.org/stable/auto_examples/model_selection/plot_precision_recall.html)
- [JSON Schema Validation specification](https://json-schema.org/draft/2020-12/json-schema-validation)
