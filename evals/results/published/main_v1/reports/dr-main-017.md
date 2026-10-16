# Small vs. Large Language Models for a Research-Agent Workflow

## Background

This report compares one small model, OpenAI GPT-4.1 mini, with one large model, Anthropic Claude Sonnet 5.5, for the supplied workload: 10,000 jobs per month, each with 50,000 input tokens and 5,000 output tokens. The run/comparison date is **2026-10-15**. This is the requested price-check date, not a verified effective date for either provider's prices.

The comparison is constrained by an important evidence gap: the official OpenAI pricing page could not be accessed in this run, so GPT-4.1 mini's rates could not be verified. Anthropic's official model overview identifies Sonnet 5.5 and the findings record its base rates as $2 per million input tokens and $10 per million output tokens. The available latency evidence is a third-party GPT-4.1 mini throughput result, not a matched comparison with Sonnet 5.5.

## Key Findings

- The workload totals **500 million input tokens and 50 million output tokens per month**.
- Using the Sonnet 5.5 rates recorded from Anthropic's official model overview, the estimated token cost is **$1,500/month**: $1,000 input plus $500 output. The separate detailed pricing page provides rates for Sonnet 4.5, not independent confirmation of Sonnet 5.5's rates. The estimate excludes caching, discounts, provider-specific billing differences, and other adjustments.
- GPT-4.1 mini's monthly cost cannot be calculated from verified evidence. If its rates are `r_in` and `r_out` USD per million input and output tokens, respectively, its cost is `500 × r_in + 50 × r_out`. It is cheaper than the Sonnet estimate only if that expression is below $1,500.
- Artificial Analysis reports GPT-4.1 mini output throughput of **151.3 tokens/second**, but the evidence does not establish a comparable Sonnet 5.5 result or end-to-end workflow latency.
- No source effective date was verified. The report uses **2026-10-15** as the run date only.

## Evidence and Analysis

### Cost calculation

Monthly token volumes:

- Input: `10,000 jobs × 50,000 input tokens/job = 500,000,000 tokens = 500 million tokens`.
- Output: `10,000 jobs × 5,000 output tokens/job = 50,000,000 tokens = 50 million tokens`.

Anthropic's official [Claude model overview](https://platform.claude.com/docs/en/models/overview) identifies Claude Sonnet 5.5 and the findings record base rates of $2 per million input tokens and $10 per million output tokens from that overview. The separate [Anthropic pricing page](https://platform.claude.com/docs/en/about-claude/pricing) provides detailed rates for Sonnet 4.5, not independent confirmation of Sonnet 5.5's rates. Thus, the calculation below uses the Sonnet 5.5 rates as recorded from the overview; the detailed pricing page is contextual evidence, not verification of those Sonnet 5.5 rates.

| Component | Monthly volume | Rate | Estimated cost |
|---|---:|---:|---:|
| Input | 500 million tokens | $2 / million | $1,000 |
| Output | 50 million tokens | $10 / million | $500 |
| **Total** |  |  | **$1,500/month** |

Formula: `monthly cost = (input tokens ÷ 1,000,000 × input rate) + (output tokens ÷ 1,000,000 × output rate)`.

The official [Anthropic pricing page](https://platform.claude.com/docs/en/about-claude/pricing) also describes cache pricing and platform/endpoint conditions. The $1,500 estimate assumes all tokens are billed at the listed standard uncached rates; it is not a guaranteed invoice. Because the detailed pricing page's rates are for Sonnet 4.5, the Sonnet 5.5 rate attribution depends on the model overview evidence summarized in the findings and should be treated with that scope in mind.

For GPT-4.1 mini, the official OpenAI pricing page could not be verified because the fetch returned HTTP 403 and search did not return the official page. Therefore, no numeric small-model cost or savings claim is supportable. With `r_in` and `r_out` as its unknown USD rates per million input and output tokens:

`C_small = 500 × r_in + 50 × r_out`.

The small model is cheaper than the Sonnet estimate only if `500 × r_in + 50 × r_out < 1,500`; equality is the break-even condition. This is a symbolic comparison, not a verified price result.

### Latency evidence and workflow implications

The third-party [Artificial Analysis GPT-4.1 mini page](https://artificialanalysis.ai/models/gpt-4-1-mini) reports 151.3 output tokens per second as a standalone GPT-4.1 mini result. That is generation throughput, not time to first token, total response time, or end-to-end agent-job duration. The page describes a default 10,000-input-token workload and notes that other workload results are historical and no longer updated. The supplied workload has 50,000 input tokens per job.

The available evidence does not provide a matched Sonnet 5.5 latency measurement. It therefore cannot establish which model is faster for this workflow. Multi-stage research agents may incur additional model calls, prompt processing, tool execution, orchestration, network delay, and retries; none of those components is quantified here. A single throughput figure should not be extrapolated into a total job-latency estimate.

### Comparative assessment

| Dimension | GPT-4.1 mini (small) | Claude Sonnet 5.5 (large) | Assessment |
|---|---|---|---|
| Public price evidence | Official pricing page inaccessible in this run; rates unverified | Model overview findings record $2/M input and $10/M output; detailed pricing page lists Sonnet 4.5 rates | Only a conditional Sonnet estimate can be calculated from the recorded overview rates |
| Estimated monthly token cost | Unknown; `500 × r_in + 50 × r_out` | $1,500 using the overview rates recorded in findings | No numeric cost winner can be declared |
| Latency evidence | 151.3 output tokens/second on a third-party page | No matched result verified | No comparative latency winner can be declared |
| Workflow fit | Requires workload-specific validation | Requires workload-specific validation | Benchmark and token assumptions do not establish quality or end-to-end performance |

## Recommendations

1. Treat **$1,500/month** as a conditional estimate using the Sonnet 5.5 rates recorded from Anthropic's model overview, under the stated uncached, standard-rate assumptions—not as a guaranteed bill. Confirm the current rate table before procurement or budgeting.
2. Before choosing on cost, verify GPT-4.1 mini's current official input/output rates and any applicable cached-input pricing, then apply the same token-volume formula.
3. For latency selection, benchmark both exact model versions on representative 50,000-input/5,000-output jobs and the actual multi-stage orchestration. Measure time to first token, per-call completion time, end-to-end job duration, concurrency effects, and retries separately.
4. If the workflow uses repeated shared context, model cache behavior explicitly rather than assuming all input tokens are billed at the uncached rate.

## Limitations

- **Price date:** 2026-10-15 is the user-specified run date. The retrieved Anthropic pages did not state a price effective date; no claim is made that the listed rates took effect on that date.
- **Small-model price gap:** The official OpenAI pricing page returned HTTP 403, and no verified GPT-4.1 mini rates were obtained. Its numeric monthly cost remains unknown.
- **Large-model rate scope:** The findings record Sonnet 5.5 rates from Anthropic's model overview, while the detailed pricing page provides Sonnet 4.5 rates. The latter does not independently verify the former; the Sonnet 5.5 estimate is conditional on the overview's recorded rates.
- **Latency gap:** The only verified latency-related figure is GPT-4.1 mini's third-party output throughput. There is no matched Sonnet 5.5 result, and the benchmark's default input size differs from the supplied workload.
- **Unsupported assumptions:** The calculation assumes the supplied token counts are billed tokens per job, all 10,000 jobs incur those volumes, and no extra calls or retries change usage. It does not model caching, discounts, taxes, provider-specific billing, endpoint premiums, concurrency, tool latency, or quality differences.
- **Source-count requirement:** The findings preserve only three distinct verified URL pages: Anthropic's model overview, Anthropic's pricing page, and Artificial Analysis's GPT-4.1 mini page. The requested minimum of five distinct source links is **not met**. The inaccessible OpenAI page is not cited as a verified source, and no irrelevant or unverified links are added to pad the count.

## References

1. Official: [Models overview - Claude Platform Docs](https://platform.claude.com/docs/en/models/overview)
2. Official: [Pricing - Claude Platform Docs](https://platform.claude.com/docs/en/about-claude/pricing)
3. Third-party benchmark: [Artificial Analysis — GPT-4.1 mini](https://artificialanalysis.ai/models/gpt-4-1-mini)

The report contains three distinct verified source links, below the requested five-source minimum, because the small-model official pricing page was inaccessible and the remaining researcher/search budget was exhausted.