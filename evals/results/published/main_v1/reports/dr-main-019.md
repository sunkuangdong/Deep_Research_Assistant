# Self-Hosting vs. Hosted Embedding API: Cost Comparison

## Background

This report compares self-hosting an embedding model with a hosted embedding API for a corpus of 1,000,000 document chunks, each 200 tokens, with 10% of the corpus re-embedded monthly and 1,000,000 query embeddings per year. The requested price date is **2026-10-15**. The research run occurred on 2026-10-16, and the available evidence does not verify prices effective on the requested date.

The workload implies 200 million tokens for the initial corpus pass and 20 million tokens per month for re-embedding. Query length was not specified; calculations that assume 200 tokens per query are explicitly illustrative, not a supplied fact.

## Key Findings

- Initial corpus embedding: **200 million tokens**.
- Monthly re-embedding: **20 million tokens**; annual re-embedding: **240 million tokens**.
- Query volume: 1 million embeddings/year, but token volume depends on average query length `q`. At an illustrative 200 tokens/query, queries add 200 million tokens/year.
- Under that query-length assumption, first-year volume is **640 million tokens** (initial corpus + annual re-embedding + queries); recurring annual volume is **440 million tokens**.
- The available official pricing evidence does not verify an embedding API rate, and the AWS pricing evidence does not verify a GPU instance rate. Model-specific throughput is also unverified. Therefore, a defensible dollar estimate or numeric cost range cannot be produced without inventing inputs.
- Self-hosting offers local inference control, but its economics depend on measured throughput, billed GPU hours/utilization, and operational overhead. Hosted API cost scales with billable tokens and avoids operating the inference fleet.

## Evidence and Analysis

### Evidence and price-date status

The [OpenAI API pricing page](https://openai.com/api/pricing/?utm_source=rachelandreago) was returned in search, but the available excerpt did not expose an embedding-specific price; page retrieval failed with HTTP 403. It therefore does not establish a rate as of 2026-10-15. The [AWS EC2 On-Demand pricing page](https://aws.amazon.com/ec2/pricing/on-demand/) findings report that the page describes hourly or per-second billing, a 60-second minimum, and no long-term commitment, but the retrieved content did not expose a GPU instance price. Region, instance type, and operating system affect the applicable rate according to the findings; the exact rate remains unverified.

For a self-hosted model example, the [BAAI/bge-small-en-v1.5 model card](https://huggingface.co/BAAI/bge-small-en-v1.5) findings report 384-dimensional output and local inference examples. The available evidence does not establish artifact size or production throughput. A [FlagEmbedding repository](https://github.com/FlagOpen/FlagEmbedding) was also consulted, but no model-specific throughput benchmark was verified. Throughput must be measured on the intended hardware and software stack.

A fifth distinct, relevant source page was not preserved in findings. The research plan targeted five pages, but the researcher delegation limit prevented additional assignments. Accordingly, this report does not meet the requested minimum of five distinct source links; it does not add unverified or irrelevant links to pad the count.

### Workload formulas

Let `q` be average query tokens per query. Assuming the 10% monthly rate applies to 10% of the full corpus each month:

- Initial tokens = `1,000,000 chunks × 200 tokens = 200,000,000`.
- Monthly re-embedding tokens = `1,000,000 × 10% × 200 = 20,000,000`.
- Annual re-embedding tokens = `20,000,000 × 12 = 240,000,000`.
- Annual query tokens = `1,000,000 × q`.
- First-year tokens = `200,000,000 + 240,000,000 + 1,000,000q`.
- Recurring annual tokens = `240,000,000 + 1,000,000q`.

At `q = 200` tokens/query, first-year volume is 640 million tokens and recurring annual volume is 440 million tokens. If queries average 50 tokens, for example, query volume is 50 million tokens/year; the actual value should use measured query lengths.

### Cost formulas, utilization, and overhead

Let `P_api` be the hosted API price in dollars per million input tokens; `H` the GPU price in dollars per billed hour for the selected region/instance/OS; `T` measured end-to-end throughput in tokens per second under the intended model, batch size, precision, and serving stack; `u` effective utilization (fraction of provisioned time doing useful embedding work); and `O` annual operational overhead in dollars. None of `P_api`, `H`, `T`, or `O` is verified by the available evidence.

- Hosted API first-year cost: `(200 + 240 + q) × P_api` dollars, where `q` is average query tokens (1 million queries × `q` tokens equals `q` million tokens).
- Hosted API recurring annual cost: `(240 + q) × P_api` dollars.
- Approximate self-hosted billed hours for `V` tokens: `V / (T × 3,600 × u)`, assuming `T` is useful tokens/second at full utilization and `u` captures effective utilization. If `T` is already measured as end-to-end throughput at observed utilization, do not divide by `u` again.
- Self-hosted first-year cost: `h_first_year × H + O_first_year + other infrastructure costs`.
- Self-hosted recurring annual cost: `h_recurring × H + O + other infrastructure costs`.
- Break-even condition: `billed GPU hours × H + O + other self-hosted costs < billable API tokens in millions × P_api`.
- Recurring break-even API price per million tokens: `(h_recurring × H + O + other costs) / (240 + q)` dollars per million tokens.

For planning, utilization must be treated as a scenario variable, not a measured fact. A sensitivity analysis could test 25%, 50%, and 75% effective utilization, but these are illustrative planning scenarios, not source-verified performance claims. A continuously provisioned GPU incurs cost during idle periods; scheduled or autoscaled capacity can reduce idle billing but may add startup delay, capacity risk, and operational complexity. A representative benchmark should include tokenization, batching, retries, and service headroom.

Operational overhead for self-hosting includes deployment and upgrades, model/runtime compatibility, monitoring, incident response/on-call, capacity planning, security, redundancy/availability, storage, networking, and engineering time. The evidence does not quantify these costs. Hosted APIs generally shift much of this operational burden to the provider, while retaining integration, data governance, rate-limit, and vendor-dependency considerations.

### Comparative assessment

| Dimension | Self-hosted | Hosted API |
|---|---|---|
| Direct cost driver | Billed compute hours, utilization, storage/networking, and operations | Billable tokens × provider rate |
| Evidence available here | Local inference path and 384-dimensional model output; no verified throughput or GPU rate | Official pricing page located, but no embedding-specific rate verified |
| Utilization sensitivity | High if capacity is always on or underused | Low direct infrastructure-utilization exposure; usage is metered by provider |
| Operational burden | Higher: deployment, scaling, monitoring, upgrades, reliability | Lower infrastructure burden; API integration and provider controls remain |
| Best fit | Sustained/high utilization, strict control/data locality, and capacity to operate inference | Variable or modest workloads, rapid deployment, and preference to avoid GPU operations |
| Main uncertainty | Throughput, GPU price, utilization, and staffing overhead | Exact price on the requested date, query token length, and provider billing details |

No numeric dollar range is defensible from the verified evidence. The correct next step for a budget is to obtain the provider’s dated embedding rate and a region-specific GPU quote, then benchmark the chosen model on representative 200-token chunks and actual query lengths. A fair comparison must also align model quality, vector dimensions, precision, batching, latency/SLA, and availability requirements.

## Recommendations

1. For a near-term deployment or uncertain/variable demand, start with a hosted API if its verified dated rate meets the budget; it avoids committing to GPU capacity and operating an inference service.
2. Evaluate self-hosting only after a representative benchmark establishes throughput and memory needs. Use the intended model, batch sizes, precision, tokenizer, and production serving stack; include headroom and idle time in billed hours.
3. Build a cost worksheet with the formulas above and at least three utilization scenarios. Include engineering/on-call time and redundancy rather than comparing API charges only with raw GPU rental.
4. Confirm average query token length and whether “10% monthly re-embedding” means 10% of the full corpus each month. This report assumes the latter.
5. Re-check official provider and cloud pricing for the exact region, instance, billing mode, and date before procurement. The requested 2026-10-15 price snapshot is not established by the evidence collected.

## Limitations

- **Price date:** The requested date is 2026-10-15, but no exact API or GPU price effective on that date was verified. The OpenAI page excerpt lacked embedding rates; AWS page output lacked GPU instance prices.
- **No dollar estimates or uncertainty ranges:** Without verified `P_api`, `H`, throughput, and operational cost, numeric cost ranges would be fabricated. The formulas are provided so these can be populated with dated quotes and benchmark results. This means the requested dollar estimate remains unresolved.
- **Query length:** The user specified 200 tokens per document chunk, not per query. Query-token totals are therefore parameterized by `q`; 200 tokens/query is only an illustrative scenario.
- **Throughput and utilization:** No reliable model-specific throughput benchmark was verified. Utilization examples are planning scenarios, not measured results.
- **Model comparability:** The self-hosted evidence concerns `BAAI/bge-small-en-v1.5`; it does not establish quality equivalence to any hosted model.
- **Operational overhead:** Staffing, monitoring, storage, networking, redundancy, and deployment costs were not quantified.
- **Source minimum:** Only four distinct source pages are linked, fewer than the requested five. The research plan targeted five pages, but the researcher delegation limit prevented additional assignments. No irrelevant or unverified links were added to pad the count.

### References

1. [Pricing | OpenAI](https://openai.com/api/pricing/?utm_source=rachelandreago) — official pricing page; embedding rate not visible in retrieved evidence.
2. [EC2 On-Demand Instance Pricing](https://aws.amazon.com/ec2/pricing/on-demand/) — official AWS pricing page; GPU rate not visible in retrieved evidence.
3. [BAAI/bge-small-en-v1.5 · Hugging Face](https://huggingface.co/BAAI/bge-small-en-v1.5) — model card.
4. [FlagEmbedding · GitHub](https://github.com/FlagOpen/FlagEmbedding) — repository; no throughput figure verified.
