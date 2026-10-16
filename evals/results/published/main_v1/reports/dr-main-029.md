# LLM-as-Judge for Agent Evaluation: Strengths, Limitations, and Practice

## Background

LLM-as-Judge uses a language model to score or compare system outputs against instructions, criteria, or reference answers. It can reduce the cost and latency of evaluating large volumes of open-ended responses, and can apply structured criteria where exact-match metrics are inadequate. For agent evaluation, however, the object being judged may include not only a final answer but also tool selection, intermediate actions, recovery from errors, and task completion. Evidence that a judge aligns with human preferences on text responses does not by itself validate it for end-to-end agent behavior.

## Key Findings

- **Useful but not bias-free:** Strong LLM judges have achieved substantial agreement with human preferences in tested response-evaluation settings, while position/order and self-enhancement biases remain documented risks.
- **Rubrics improve explicitness, not automatic validity:** Task-specific criteria and structured scoring can make judgments more reproducible than an unstructured rating prompt. Rubric transferability and sensitivity to wording still require testing.
- **Blinding is a safeguard, not an established universal practice:** The reviewed evidence does not establish systematic blinding of system identity/provenance. Neutral randomized labels are a recommended control, not a demonstrated result across the studies reviewed.
- **Calibration and agreement need separate reporting:** Human calibration details are not verifiable in one assigned source. Correlation, raw agreement, and chance-adjusted agreement answer different questions and should not be conflated.
- **Agent-specific validity remains uncertain:** A recent benchmark abstract reports evaluation of 54 judges on RAG or agentic pipeline responses and uses Cohen’s kappa after correlation screening. The available abstract does not establish that complete trajectories, intermediate tool calls, or safety/process quality were evaluated. This source was successfully fetched in this run but was not preserved in a researcher findings file; its URL is therefore omitted from the references and the details are supplementary rather than fully traceable report evidence.

## Evidence and Analysis

### Model bias and blinded labels

Zheng et al.’s MT-Bench/Chatbot Arena study identifies position bias: pairwise judgments can change with candidate order. It also identifies self-enhancement bias, in which a judge may favor outputs from itself or a similar model. The study reports that strong judges such as GPT-4 can exceed 80% agreement with human preferences in the tested settings. This supports the practical value of LLM judging, but aggregate agreement does not show that systematic biases are absent. Reversing candidate order and aggregating judgments is a useful robustness check; it is not a universal correction, and the evidence reviewed does not quantify its effectiveness for tool-using agents.

G-Eval provides a concrete example of structured judging: it uses task-specific criteria, generated evaluation steps, and a score form. It reports a Spearman correlation of 0.514 with human judgments for GPT-4 on summarization. The paper also notes evaluator preference for LLM-generated text. The accessible evidence does not establish a systematic blinded-label protocol. Therefore, identity blinding should be treated as a recommended experimental control: replace system names with randomized neutral identifiers and withhold the mapping from judges and human raters until scoring is complete. Blinding can reduce identity-driven preference, but cannot remove preferences triggered by observable style or content.

### Rubric design and human calibration

Explicit criteria and scoring anchors help define what the judge is meant to measure. For agents, a rubric should distinguish outcome correctness from process quality—for example, whether the task was completed, whether tools were selected and used appropriately, whether intermediate constraints were respected, and whether the agent recovered safely from errors. These are recommendations for construct coverage, not findings that one rubric is optimal. Exact prompts, model/version, score scale, decoding settings, and aggregation rules should be documented because they are part of the measurement protocol.

Human calibration is necessary to make the reference judgments interpretable. The reviewed evidence does not provide verifiable details on rater training, calibration exercises, adjudication, or human-rater reliability for the assigned agent-evaluation source; this is an evidence gap, not proof that those practices were absent. A recent arXiv abstract, “Judge’s Verdict,” describes 54 LLM judges evaluated on RAG or agentic pipeline responses and a two-stage approach that moves from correlation to Cohen’s kappa agreement-pattern analysis. It reports 27 Tier 1 models, including 23 classified as human-like and four as super-consistent. This is relevant to agreement reporting, but the abstract alone does not establish human-rater calibration, the operational definitions behind those categories, or full trajectory coverage. This source was successfully fetched during this run, but was not preserved in a researcher findings file; its URL is not included in the references below and these abstract-level details should be treated as supplementary evidence rather than a fully traceable report citation.

### Agreement reporting and agent validity

Correlation measures association or ranking alignment; it does not necessarily show that two raters assign the same labels. Cohen’s kappa can characterize chance-adjusted categorical agreement, but its interpretation depends on the label structure and prevalence. A robust report should state the unit of analysis, label categories, raw agreement, chance-adjusted agreement, uncertainty intervals, disagreement patterns, and handling of ties or missing judgments. Where multiple human raters are involved, report their agreement and calibration separately from agreement between the LLM judge and the human reference.

The evidence spans open-ended assistant responses and summarization/dialogue tasks. The supplementary “Judge’s Verdict” abstract describes RAG/agentic pipeline responses, but it does not establish that the same judge protocol reliably evaluates complete agent trajectories across tasks. In particular, final-answer scoring may miss tool misuse, unsafe intermediate actions, or brittle recovery behavior. Agent-specific validation should therefore use representative trajectories and failure modes, not only final outputs.

## Recommendations

1. **Define the construct before selecting a judge.** Specify whether the target is final-answer correctness, task completion, process quality, tool-use appropriateness, safety, or a combination. Use separate rubric dimensions where these constructs can diverge.
2. **Use explicit, task-specific rubrics.** Provide observable criteria, anchored score levels, tie/abstention rules, and examples. Test rubric sensitivity to wording and across task types rather than assuming transferability.
3. **Blind and counterbalance where feasible.** Replace system identities with randomized labels; randomize candidate order and, for pairwise comparisons, score both orders. Report order-flip rates and identity-related subgroup results.
4. **Calibrate against humans.** Train raters on the rubric, run calibration examples, document adjudication, and measure human-human reliability before treating human labels as a gold standard. Periodically audit a representative sample of judge decisions.
5. **Report agreement comprehensively.** Present correlation separately from raw and chance-adjusted agreement (such as Cohen’s kappa for suitable categorical labels), with uncertainty and disagreement patterns. Explain prevalence, ties, missing data, and the unit of analysis.
6. **Validate on full agent behavior.** Include tool calls, intermediate steps, task outcomes, and failure/recovery cases when those are part of the intended construct. Compare judge scores with calibrated human assessments and task-grounded outcomes; do not infer trajectory validity from response-level alignment alone.
7. **Make the protocol reproducible.** Publish the judge model/version, prompts, rubric, candidate presentation, decoding settings, aggregation method, and any filtering or adjudication rules.

## Limitations

The evidence base available for this report is uneven. The G-Eval and MT-Bench/Chatbot Arena findings are supported by accessible arXiv records, but detailed methods and effect sizes are not fully available in the retrieved material. The assigned Nature target page could not be verified, so its calibration and agreement practices remain unknown; this should not be interpreted as evidence that it omitted them. The “Judge’s Verdict” evidence is available through its successfully fetched arXiv abstract page, which does not provide enough methodological detail to assess its kappa implementation, category definitions, uncertainty estimates, or whether it evaluates complete agent trajectories. However, because that source was not preserved in a researcher findings file, it is not included as a reference link and its details are supplementary rather than fully traceable. **The final report does not meet the requested minimum of five distinct source links:** only two distinct verified source URLs were preserved in findings. The failed Nature retrieval is not citable, and no additional verified sources were available within the remaining researcher delegation budget. No irrelevant or unverified links have been added to pad the count. Generalization across judge models, agent tasks, and deployment settings therefore remains uncertain.

## References

- [Zheng et al., “Judging LLM-as-a-Judge with MT-Bench and Chatbot Arena”](https://arxiv.org/abs/2306.05685)
- [Liu et al., “G-Eval: NLG Evaluation using GPT-4 with Better Human Alignment”](https://arxiv.org/abs/2303.16634)

Source note: These are the two distinct source pages preserved in findings and traceable to this run. The assigned Nature target page could not be verified (HTTP 404). The “Judge’s Verdict” page was successfully fetched, but its URL was not preserved in findings and is therefore omitted from the references.