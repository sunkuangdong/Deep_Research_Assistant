---
name: deep-research
description: Use this skill when the user asks for deep research, multi-source investigation, evidence-based comparison, market or technical analysis, or a structured research report.
---

# Deep Research Skill

## Purpose

Use this skill to conduct structured deep research for complex questions that require planning, source collection, evidence comparison, analysis, and a final report.

This project is a Chinese Deep Research Assistant. Unless the user explicitly asks otherwise, all final outputs must be written in Chinese.

## When To Use

Use this skill when the task involves:

- Deep research or comprehensive investigation
- Comparing frameworks, products, companies, papers, models, or technical solutions
- Collecting evidence from multiple sources
- Producing a structured research report
- Explaining trade-offs, trends, risks, or recommendations
- Answering questions that require source-aware synthesis

Do not use this skill when:

- The user only asks for a simple fact
- The answer can be completed from local project context only
- No research, synthesis, or comparison is needed

## Research Workflow

Follow this workflow:

1. Restate the research goal in one sentence.
2. Break the topic into 2-4 focused subquestions.
3. For each subquestion, collect evidence from reliable sources.
4. Prefer primary and high-trust sources:
   - Official documentation
   - Vendor announcements
   - Standards or specifications
   - Academic papers
   - Reputable engineering blogs
   - Well-known technical communities
5. Compare findings across sources.
6. Separate facts, interpretations, and assumptions.
7. Identify uncertainty, conflicts, and missing information.
8. Synthesize the final answer into a structured Chinese report.

## Subagent Strategy

When subagents are available, use them as follows:

- Use researcher subagents for focused subtopic investigation.
- Each researcher should handle only one focused subtopic.
- Use analyst subagents for comparison, trend analysis, trade-off analysis, or structured reasoning.
- Use editor subagents to review clarity, evidence quality, and final report structure.
- Do not delegate unnecessary work just to use more subagents.

## Evidence Requirements

For important claims:

- Prefer claims backed by sources.
- Include source URLs or source names when available.
- Mark weakly supported claims as uncertain.
- Do not invent numbers, rankings, benchmarks, or dates.
- If sources conflict, explain the conflict instead of hiding it.

## Output Format

The final report should usually include:

1. Background
2. Key Findings
3. Evidence and Analysis
4. Comparison or Trade-offs
5. Recommendations
6. Limitations and Uncertainties

Keep the language professional, concise, and Chinese-first.