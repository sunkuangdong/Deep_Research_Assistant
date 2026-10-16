# Dense, Sparse, and Hybrid Retrieval for Technical Support Knowledge Bases

## Background

Technical support knowledge bases must answer at least two different query types: literal lookups for error codes, product or model identifiers, versions, API names, and commands; and descriptive searches where users explain symptoms in their own words. Sparse (lexical) retrieval, dense (embedding-based) retrieval, and hybrid retrieval address these needs differently. The evidence reviewed here combines official Elasticsearch documentation with general information-retrieval research; it does not include a direct head-to-head benchmark on a technical-support corpus.

## Key Findings

- **Sparse retrieval has the clearest direct documentation support for exact identifiers in the evidence reviewed; this is not a measured performance ranking.** Elasticsearch documents `keyword` fields and term-level queries for IDs and status codes, including numeric identifiers searched as exact terms. Correct mapping, normalization, and handling of long values matter.
- **Dense retrieval is useful for semantic variation, not guaranteed literal identity.** Dual-encoder retrieval can match related query and passage meanings despite wording differences. It should not be treated as an exact-match mechanism for codes or version strings.
- **Hybrid retrieval is a strong candidate when both query types matter.** Reciprocal rank fusion (RRF) combines ranked lists without adding raw scores from different scales. Its parameters and performance trade-offs still require corpus-specific tuning.
- **Reranking is a second-stage option, not a substitute for retrieval coverage.** Cross-encoders jointly score query–passage pairs and can reorder candidates, but the cited comparison used SPLADE candidates, not dense candidates or support articles; transfer and latency must be tested.
- **Evaluation should separate exactness from semantic relevance.** Compare sparse-only, dense-only, and hybrid systems on the same held-out queries, with explicit identifier and paraphrased-symptom categories, relevance judgments, ranking metrics at operational cutoffs, and latency measurements where reranking is used.

## Evidence and Analysis

### Sparse / lexical retrieval

Sparse retrieval is a natural baseline for exact technical tokens because it can match indexed terms and structured values. Elasticsearch’s [keyword field documentation](https://www.elastic.co/docs/reference/elasticsearch/mapping-reference/keyword) identifies IDs and status codes as suitable keyword content and discusses exact term queries. It also notes mapping considerations: a keyword field is not normalized by default unless configured, and dynamically mapped `.keyword` subfields may omit values beyond `ignore_above`. These details make schema and query handling part of retrieval quality, not merely implementation housekeeping.

Tokenization and stemming can also affect technical vocabulary in prose fields. An older Elasticsearch [keyword-marker filter reference](https://www.elastic.co/guide/en/elasticsearch/reference/5.3/analysis-keyword-marker-tokenfilter.html) describes protecting selected terms from stemming, but it is an unmaintained version and should be treated as conceptual evidence rather than current configuration advice.

**Trade-off:** lexical retrieval is well suited to literal identifiers and terms, but may miss relevant content when the user describes a problem with different wording. Exactness is conditional on field mapping, analyzers, normalization, and query construction.

### Dense retrieval and reranking

Dense dual encoders represent queries and passages separately and retrieve candidates by vector similarity. This can help when a user’s symptom description differs lexically from the wording in a troubleshooting article. The cited general research on [dual-encoder dense retrieval](https://arxiv.org/abs/2303.14991) supports the architecture, but does not establish performance on support knowledge bases or exact-identifier queries.

A retrieve-then-rerank pipeline can retrieve a candidate set first and then use a cross-encoder to score query–passage pairs jointly. The cited [reranking comparison](https://arxiv.org/abs/2403.10407) reports domain-dependent differences and sensitivity to the number of documents reranked; its experiments use SPLADE candidates, so they do not directly prove the same gains for dense candidates or support content. Reranking can improve ordering only among retrieved candidates, and adds computation and latency.

**Trade-off:** dense retrieval is attractive for paraphrases and symptom descriptions, but semantic similarity does not guarantee literal token identity. Reranking may improve candidate ordering, but its effectiveness and cost depend on the corpus, candidate source, and depth.

### Hybrid retrieval and fusion

Hybrid retrieval combines lexical and vector result lists. Elasticsearch’s [RRF documentation](https://www.elastic.co/docs/reference/elasticsearch/rest-apis/reciprocal-rank-fusion) describes rank-based fusion, which avoids directly adding raw scores that may be on incomparable scales. The documented implementation exposes `rank_constant` and `rank_window_size`; larger windows can improve relevance at a performance cost. These are implementation facts, not evidence that RRF is universally superior or that its defaults are optimal for support content.

**Trade-off:** hybrid retrieval can cover both exact terms and semantic variation, but adds system complexity and requires tuning. RRF is one fusion option; its support-domain benefit must be measured against each component retriever.

### Comparative view

| Dimension | Sparse / lexical | Dense | Hybrid |
|---|---|---|---|
| Exact identifiers | Strong fit when identifiers are indexed and queried as exact values; mapping and normalization are critical. | Similarity does not guarantee literal identity; direct support-domain evidence is absent. | Lexical results can contribute exact matches while dense results contribute semantic candidates; benefit must be validated. |
| Semantic matching | Limited when query wording differs from document wording. | Strong candidate for paraphrases and symptom descriptions. | Can combine lexical and semantic coverage. |
| Reranking / fusion | Can supply candidates; no support-specific reranking result established here. | Cross-encoder reranking is plausible, but cited evidence does not directly test dense candidates in support KBs. | RRF fuses ranked lists; it is distinct from cross-encoder reranking and has tunable relevance/performance parameters. |
| Main operational concern | Analyzer, field mapping, normalization, and identifier length. | Candidate recall, exactness risk, and inference/reranking latency. | Added complexity, fusion tuning, and the need to compare against component baselines. |

## Recommendations

1. **Start with a representative evaluation set, not an assumed winner.** Include exact error codes, product/model IDs, versions, API and command names, and natural-language symptom paraphrases. Use the same held-out queries and article- or passage-level relevance judgments for all systems.
2. **Establish sparse and dense baselines, then test hybrid.** As a recommended evaluation design—not a protocol established by the cited sources—report ranking quality at operational cutoffs (for example, Recall@k and nDCG@k) and separately track exact-identifier success and symptom-paraphrase success. Aggregate relevance alone can hide identifier failures.
3. **Treat identifier handling as an explicit design requirement.** Validate field mappings, analyzers, normalization, and long-value behavior. Do not rely on dense similarity or a semantic reranker as proof that an exact code or version was matched.
4. **Add reranking only when measured gains justify its cost.** Vary candidate depth and measure both ranking effectiveness and latency on the actual support corpus and candidate source.
5. **Tune fusion on held-out queries.** If using RRF, test `rank_window_size` and, where appropriate, `rank_constant`; do not assume documented defaults are optimal for the knowledge base.

## Limitations

The available evidence does not directly compare sparse, dense, and hybrid retrieval on a technical-support knowledge base. The dense and reranking papers provide general IR evidence; the reranking comparison uses SPLADE candidates rather than dense candidates. The RRF documentation describes implementation behavior and parameters, not support-domain effectiveness. The keyword-marker reference is for Elasticsearch 5.3 and is unmaintained. No corpus, query distribution, relevance judgments, latency target, or support outcome data were provided, so the recommendations are an evaluation plan rather than a corpus-specific performance conclusion.

### References

- [Keyword type family — Elasticsearch Reference](https://www.elastic.co/docs/reference/elasticsearch/mapping-reference/keyword)
- [Keyword Marker Token Filter — Elasticsearch Guide 5.3](https://www.elastic.co/guide/en/elasticsearch/reference/5.3/analysis-keyword-marker-tokenfilter.html)
- [Empowering Dual-Encoder with Query Generator for Cross-Lingual Dense Retrieval](https://arxiv.org/abs/2303.14991)
- [A Thorough Comparison of Cross-Encoders and LLMs for Reranking SPLADE](https://arxiv.org/abs/2403.10407)
- [Reciprocal rank fusion — Elasticsearch documentation](https://www.elastic.co/docs/reference/elasticsearch/rest-apis/reciprocal-rank-fusion)
