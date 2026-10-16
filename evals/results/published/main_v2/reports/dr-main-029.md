# LLM-as-Judge for Agent Evaluation: Strengths, Limitations, and Practice

## Background

LLM-as-Judge uses a language model to score, rank, or explain the quality of model outputs. It is attractive for agent evaluation because it can scale beyond manual review and apply a consistent rubric across many runs. Research on text-generation and dialogue evaluation reports meaningful alignment with human preferences, while also documenting systematic biases and limits to transfer. The evidence reviewed here includes five distinct primary research pages: MT-Bench/Chatbot Arena, two studies of judge bias, G-Eval, and LLM-Rubric. The strongest direct evidence concerns text and dialogue outputs; it does not establish validity for autonomous agents’ full tool-use trajectories.

## Key Findings

- **Scalability and human alignment are real strengths, but not guarantees of validity.** G-Eval reports a Spearman correlation of 0.514 with human judgments in a summarization experiment. MT-Bench/Chatbot Arena reports substantial alignment between strong judges and human preferences. These results support LLM judges as useful measurement aids in studied settings, not as universal replacements for human evaluation. [G-Eval](https://arxiv.org/abs/2303.16634); [MT-Bench and Chatbot Arena](https://arxiv.org/abs/2306.05685)
- **Bias can affect rankings independently of task quality.** Research identifies position/order, verbosity, and self-enhancement biases; separate work studies position consistency and preference fairness, while another proposes a framework to quantify multiple biases. Blinding agent/model labels is a plausible control for identity favoritism, but the reviewed evidence does not show that blinding alone removes bias. [MT-Bench and Chatbot Arena](https://arxiv.org/abs/2306.05685); [Position Bias Study](https://arxiv.org/abs/2406.07791); [CALM bias study](https://arxiv.org/abs/2410.02736)
- **Explicit, multidimensional rubrics can make judgments more interpretable and calibratable.** G-Eval uses task-specific criteria and structured form-filling. LLM-Rubric uses multiple questions for separate dimensions and reports improved calibrated satisfaction prediction in a dialogue setting. These findings do not validate a universal rubric for agents. [G-Eval](https://arxiv.org/abs/2303.16634); [LLM-Rubric](https://arxiv.org/html/2501.00274v1)
- **Human calibration helps in a studied setting, but transfer is uncertain.** LLM-Rubric reports lower prediction error after calibration against multiple annotators, while also finding that personalized calibration alone was insufficient. Human ratings themselves can vary, so human-human agreement should be measured rather than assuming a perfect gold standard. [LLM-Rubric](https://arxiv.org/html/2501.00274v1)
- **Agreement reporting must go beyond correlation.** Correlation captures association or ranking tendency, not whether judges assign the same score or label. Report complementary, scale-appropriate agreement/error measures and human-human agreement, with sample size and uncertainty.

## Evidence and Analysis

### Bias and blinded labels

Pairwise judging is vulnerable to presentation effects: candidate order, verbosity, and judge preferences can influence outcomes. Position-bias research treats consistency and fairness as measurable properties, supporting repeated or counterbalanced judgments rather than assuming one order swap fixes the problem. Blinding labels can reduce explicit identity cues when identity is irrelevant, but it cannot necessarily prevent identity inference from content and does not address order effects. The evidence reviewed does not quantify a general causal benefit of blinding; it should be treated as a control to test, not a proven cure.

### Rubric design and human calibration

A rubric should define observable criteria and score anchors rather than ask for an undifferentiated “best” answer. Multidimensional criteria can separate correctness, completeness, evidence quality, and communication, and for agents can distinguish task outcome from process/tool-use quality. However, more dimensions also increase authoring and validation burden; vague or overlapping criteria can create false precision. Pilot rubrics with human raters, inspect disagreements, revise ambiguous anchors, and freeze the rubric before comparing systems.

Calibration should use a representative sample from the target task and population, with multiple human ratings where feasible. The LLM-Rubric results show that calibration can improve predictions in a particular dialogue dataset, but do not establish transfer across tasks, judge models, prompts, or annotator populations. Human disagreement is part of the measurement problem, not noise that can simply be ignored.

### Agreement and agent-specific validity

Report at least one association measure and one agreement/error measure suited to the score scale. For ordinal ratings, weighted kappa and exact/adjacent agreement may be informative; for numeric scores, MAE or RMSE can complement rank correlation. Also report sample size, uncertainty, and human-human agreement. No single statistic captures all relevant properties.

A key validity gap is the difference between judging a final text response and judging an agent’s trajectory. Tool calls, observations, intermediate decisions, recovery behavior, and terminal outcomes may matter even when the final answer sounds fluent. The reviewed studies provide a starting point for final-output evaluation, but direct evidence for general tool-using agent trajectories is limited. Agent evaluations should preserve and score relevant trajectory evidence and validate those criteria against human judgments and task outcomes.

## Recommendations

1. **Use LLM judges as scalable aids, not unvalidated substitutes for human review.** Retain human audits for consequential comparisons and investigate disagreements.
2. **Control and measure order effects.** Randomize or counterbalance candidate order, repeat judgments with swapped order, and report position consistency or disagreement. Treat this as a diagnostic and control, not a guaranteed correction.
3. **Blind labels where feasible, then test the control.** Remove explicit agent/model names and irrelevant identity cues; assess whether identity remains inferable and remember that blinding does not address position or verbosity bias.
4. **Use an operational, multidimensional rubric.** Define observable evidence, explicit score anchors, and rules for missing evidence. For agents, separate outcome correctness from process/tool-use quality when both matter.
5. **Calibrate and validate on the target setting.** Compare judge scores with multiple human ratings on a representative sample; measure human-human agreement; revalidate after changes to the judge, prompt, rubric, task distribution, or annotator population.
6. **Report complementary agreement statistics.** Pair correlation with scale-appropriate agreement/error measures, and disclose sample size and uncertainty. Choose metrics before inspecting system rankings where practical.
7. **Evaluate trajectories as trajectories.** Include relevant actions, tool calls, observations, intermediate decisions, and terminal outcomes rather than scoring only the final response.

## Limitations

The evidence base is small and primarily concerns summarization, dialogue generation, and dialogue-system outputs. Transfer to autonomous agents and multi-step tool-use trajectories is not established. The findings do not provide comparable effect sizes across bias studies or quantify the general benefit of blinding, order counterbalancing, or specific mitigation strategies. Calibration results are dataset- and annotator-pool-specific, and human judgments are not a perfect ground truth. Some methodological details were available only in the findings summaries; conclusions should therefore be treated as evidence-informed guidance rather than universal guarantees.

### References

1. Zheng et al., “Judging LLM-as-a-Judge with MT-Bench and Chatbot Arena.” https://arxiv.org/abs/2306.05685
2. “Judging the Judges: A Systematic Study of Position Bias in LLM-as-a-Judge.” https://arxiv.org/abs/2406.07791
3. “Justice or Prejudice? Quantifying Biases in LLM-as-a-Judge.” https://arxiv.org/abs/2410.02736
4. Liu et al., “G-Eval: NLG Evaluation using GPT-4 with Better Human Alignment.” https://arxiv.org/abs/2303.16634
5. Hashemi et al., “LLM-Rubric: A Multidimensional, Calibrated Approach to Automated Evaluation of Natural Language Texts.” https://arxiv.org/html/2501.00274v1
