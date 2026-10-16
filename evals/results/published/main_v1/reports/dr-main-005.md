# Dense, Sparse, and Hybrid Retrieval for Technical Support Knowledge Bases

## Background

**Executive summary.** Sparse retrieval is a practical foundation for literal technical identifiers only when indexing and tokenization preserve them; exact-match fields or constraints should complement BM25. Dense retrieval can improve semantic recall for differently worded symptoms, but the cited studies do not establish reliable handling of rare identifiers or version distinctions in support corpora. Hybrid retrieval is a candidate for mixed query populations, while reranking can improve ordering only among retrieved candidates and adds cost and latency. No universal winner is established: evaluate on held-out, support-specific queries and measure ranking quality alongside latency and cost.

Technical support knowledge bases contain both natural-language descriptions and brittle literal strings: error codes, product and model names, software versions, command flags, and configuration keys. A user may quote an identifier exactly, describe a symptom in different words, or combine both. Retrieval therefore needs to balance literal matching with semantic matching, while keeping the first-stage candidate set relevant enough for any later reranker.

The evidence reviewed here includes Elasticsearch documentation, research on dense passage retrieval and sentence embeddings, the BEIR benchmark, and reranking documentation. These sources establish general retrieval properties and design considerations, but none directly compares all approaches on a specific technical-support knowledge base.

## Key Findings

### Sparse retrieval and exact identifiers

Elasticsearch documents BM25 as its default text similarity and supports field-level similarity configuration for text-oriented fields, including `text` and `keyword`; it also documents boolean similarity for match-oriented cases. This makes lexical retrieval a natural baseline for queries containing literal identifiers. In a support index, a practical design is to keep analyzed prose searchable while preserving identifiers in exact-match representations or fields. Analyzer behavior should be tested against real punctuation, case, separators, and version syntax. These schema and analyzer recommendations are implementation guidance, not a support-specific result established by the documentation. [Elasticsearch similarity documentation](https://www.elastic.co/docs/reference/elasticsearch/mapping-reference/similarity)

BM25 ranks by lexical evidence; it does not guarantee that the top result is the correct incident or version. Exact identifier matches may need explicit fields, constraints, or boosts, and version metadata should be checked rather than inferred from general text relevance.

### Dense retrieval and semantic matching

Dense Passage Retrieval (DPR) uses question and passage encoders to retrieve by learned representations. On the open-domain QA datasets reported in its paper, DPR exceeded a strong Lucene-BM25 baseline by 9–19 percentage points in top-20 passage retrieval accuracy. Sentence-BERT uses sentence embeddings for efficient similarity search; its paper reports a 10,000-sentence all-pairs example reduced from about 65 hours to about 5 seconds compared with the stated cross-encoder setup. These are task-specific research results, not expected gains or latency estimates for a support deployment. [DPR paper](https://arxiv.org/abs/2004.04906); [Sentence-BERT paper](https://arxiv.org/abs/1908.10084)

The practical role of dense retrieval is to find semantically related passages when query and article wording differ. The cited studies do not quantify performance on rare error codes, product/version distinctions, command flags, negation, or near-duplicate troubleshooting steps. Dense retrieval should therefore be treated as a semantic recall mechanism, not as a substitute for exact identifier handling.

### Hybrid retrieval and reranking

BEIR evaluates retrieval systems across 18 datasets and varied tasks. It reports BM25 as a robust baseline and finds reranking and late-interaction models achieve the best average zero-shot performance at higher computational cost, while dense and sparse retrieval are more efficient but often underperform in that benchmark. This supports evaluating quality and cost together, but does not predict results on a support corpus. [BEIR paper](https://arxiv.org/abs/2104.08663)

Hybrid retrieval can combine lexical candidates that match exact terms with dense candidates that match paraphrased symptoms. Reciprocal Rank Fusion (RRF) is a rank-level fusion approach that can combine lists without requiring raw scores from different retrievers to be calibrated to the same scale. In this run, the RRF primary PDF was not verified; the available evidence is an abstract-level secondary record, so its reported experimental gains should not be treated as a guarantee for support search. [RRF paper record](https://readpaper.com/paper/2148972377)

A reranker can reorder a bounded candidate set by query relevance, but it cannot recover a relevant article that the first-stage retriever failed to retrieve. Cohere’s documentation describes reranking as sorting text inputs by semantic relevance and notes token limits and automatic chunking behavior for over-limit documents. Candidate count, document length, chunking, latency, and cost should be measured in the target system. [Cohere Rerank documentation](https://docs.cohere.com/docs/rerank.md)

## Evidence and Analysis

| Approach | Exact identifiers | Semantic matching | Trade-offs and suitable scenarios |
|---|---|---|---|
| Sparse / lexical | A practical design fit for literal codes and names only when indexing preserves them; exact fields and analyzer validation matter. This is not a demonstrated support-corpus performance advantage. | Limited when query and article have little lexical overlap. | Efficient baseline and useful to test for identifier-heavy queries. BM25 alone does not ensure version correctness or top-result accuracy. |
| Dense | The reviewed evidence does not establish reliable exact-identifier discrimination. | Useful for paraphrases and varied symptom descriptions. | Appropriate as a semantic candidate generator. Benchmark results from open-domain QA do not transfer automatically to support search. |
| Hybrid / fusion | Retains a lexical path for exact terms while adding semantic candidates. | Covers complementary lexical and semantic query types. | A reasonable candidate for mixed support traffic. Fusion settings and candidate windows require local tuning; no universal best configuration is established. |
| Reranking | Can reorder candidates but does not itself guarantee exact identifier correctness. | Can refine semantic relevance among retrieved candidates. | Useful when first-stage retrieval has adequate recall but ordering is weak. Adds compute/latency and depends on candidate coverage and document handling. |

The evidence favors a complementary architecture rather than an exclusive choice: preserve exact identifiers through lexical fields or constraints, add dense retrieval for semantic variation, fuse candidate lists, and apply reranking only if local measurements justify it. This is a reasoned design recommendation, not a directly tested support-domain winner. The available studies and documentation do not provide comparable support-corpus measurements for quality, latency, or cost.

### Evaluation strategy

Build a held-out query set from real support traffic and label relevant articles or passages. Stratify it at minimum into: exact identifiers/error codes; product- and version-specific questions; paraphrased symptoms; and ambiguous or multi-step issues. Compare sparse, dense, hybrid/fused, and reranked pipelines on the same corpus and query set.

Report candidate coverage (for example, Recall@k), top-rank quality (for example, MRR or nDCG@k), and operational latency and cost. Inspect exact-identifier and version-specific cases separately, including analyzer/normalization behavior. Measure reranking at realistic candidate counts and document lengths. If retrieval feeds a RAG system, supplement ranking metrics with downstream answer resolution or task success: traditional ranking metrics may not fully reflect how a model consumes a set of retrieved documents. This evaluation protocol is a recommendation; it is not an experiment reported by the cited sources.

## Recommendations

1. **Start with a lexical baseline and explicit identifier preservation.** Keep exact identifiers searchable without relying solely on prose tokenization; validate analyzers against representative codes, versions, and configuration keys.
2. **Add dense retrieval for semantic coverage.** Test paraphrased symptoms and user language that differs from article wording, while retaining exact-match safeguards.
3. **Evaluate hybrid fusion as the likely mixed-query candidate.** Compare rank fusion such as RRF with alternatives on held-out support queries; tune candidate windows and fusion settings rather than assuming defaults are optimal.
4. **Add reranking selectively.** Use it when relevant candidates are present but poorly ordered, and retain it only if measured relevance gains justify latency and cost.
5. **Make evaluation query-stratified and operational.** Track Recall@k, MRR or nDCG@k, exact-identifier/version correctness, downstream resolution where applicable, latency, and cost. Reassess with representative traffic and relevance judgments before deployment decisions.

## Limitations

- No cited source directly evaluates dense, sparse, hybrid, and reranked retrieval on the target technical-support knowledge base. Transfer from open-domain QA, general benchmarks, and vendor documentation is uncertain.
- The RRF primary PDF was not verified; its evidence is limited to a secondary abstract-level record. Exact experimental details and reported gains remain unverified.
- No local query distribution, relevance judgments, identifier error rates, latency measurements, or cost measurements were available. Therefore, no deployment-specific winner or expected gain can be stated.
- The dense-retrieval evidence does not quantify rare-identifier, negation, version-specific, or near-duplicate troubleshooting performance. The sparse documentation does not establish support-specific analyzer behavior or retrieval quality.
- BEIR’s quality/cost observations are benchmark-level, not deployment measurements. Cohere’s reranking documentation is vendor documentation, not an independent support-corpus evaluation.
- The evaluation recommendations are proposed for this use case; they should be adapted to the knowledge base’s actual user tasks and success criteria.

**References**

1. [Elasticsearch similarity documentation](https://www.elastic.co/docs/reference/elasticsearch/mapping-reference/similarity)
2. [Dense Passage Retrieval for Open-Domain Question Answering](https://arxiv.org/abs/2004.04906)
3. [Sentence-BERT: Sentence Embeddings using Siamese BERT-Networks](https://arxiv.org/abs/1908.10084)
4. [BEIR: A Heterogeneous Benchmark for Zero-shot Evaluation of Information Retrieval Models](https://arxiv.org/abs/2104.08663)
5. [Reciprocal rank fusion paper record](https://readpaper.com/paper/2148972377) — secondary record; primary PDF not verified in this run.
6. [Cohere Rerank documentation](https://docs.cohere.com/docs/rerank.md)
