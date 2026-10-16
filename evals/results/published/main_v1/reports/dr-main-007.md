# Reference Architecture: Multi-Tenant RAG Service

## Background

A multi-tenant retrieval-augmented generation (RAG) service must preserve tenant and document authorization across the full lifecycle: source upload, asynchronous parsing and embedding, vector/index storage, retrieval, model context construction, citations, and deletion or re-indexing. A single tenant filter at query time is not enough if ingestion jobs, caches, conversation state, or citations can cross boundaries. The architecture below combines resource isolation choices with application-enforced identity, durable asynchronous processing, and evidence-bound citations.

## Key Findings

1. **Isolation is layered.** AWS SaaS Lens describes silo, pool, and bridge resource patterns. These are deployment choices, not replacements for authorization. Tenant scope must remain consistent across documents, chunks, embeddings, indexes, caches, histories, and outputs.
2. **Ingestion is eventually consistent.** S3 notifications are at-least-once, may be delayed, and are not guaranteed to arrive in order. Workers therefore need idempotency, version/state guards, deletion tombstones, and reconciliation.
3. **Authorization must precede model context.** Metadata filters can constrain vector search, but filter capability alone is not an authorization system. Derive tenant scope from authenticated server-side identity and enforce tenant plus document ACL predicates before retrieved content reaches the model.
4. **Citations need application-maintained provenance.** Preserve immutable document/version IDs and chunk/source spans during ingestion; bind citations to authorized retrieval results and validate them. Do not rely on model-generated source identifiers or locations.
5. **Re-indexing should publish complete generations.** Track desired and indexed versions, build a new generation off-path, and expose it only after all chunks are committed; use an atomic pointer/swap or equivalent to avoid mixed-version retrieval.

## Evidence and Analysis

### Proposed logical architecture

```text
Client
  │ authenticated request
  ▼
API gateway / identity layer ──► tenant membership + policy service
  │                                  │ trusted tenant/principal context
  ├── upload/control API             ▼
  │     │                       Query orchestrator
  │     ▼                            │ mandatory tenant + ACL predicates
  │  Object storage                  ▼
  │     │ events                 Retrieval service / vector index
  │     ▼                            │ authorized chunks only
  │  Durable queue                   ▼
  │     ▼                       Context builder + citation validator
  │  Ingestion workers               │
  │  parse → chunk → embed            ▼
  │     │                       LLM / response
  │     ▼                            │
  └─► metadata + index registry ◄─────┘ citations resolve to source records
       (desired/indexed version, ACL, generation, tombstone)
```

The diagram is logical rather than vendor-specific. The identity layer authenticates the caller and resolves tenant membership. The service, not the client or model, supplies trusted tenant context to downstream components. The policy service evaluates document-level permissions and returns or compiles predicates for retrieval. Background jobs carry a tenant-scoped service identity and immutable object/version reference.

### Isolation and authorization

Choose **silo** for tenants whose regulatory, contractual, or blast-radius requirements justify dedicated resources; **pool** where shared infrastructure is acceptable and mandatory tenant-aware controls can be reliably enforced; and **bridge** where tenant or component risk profiles differ. AWS SaaS Lens describes these as resource-footprint patterns, not substitutes for authorization ([tenant isolation](https://docs.aws.amazon.com/wellarchitected/latest/saas-lens/tenant-isolation.html); [silo, pool, and bridge models](https://docs.aws.amazon.com/wellarchitected/latest/saas-lens/silo-pool-and-bridge-models.html)). In all cases, enforce authorization independently of resource layout. For pooled indexes, tenant and document ACL filters must be mandatory and server-generated. For silo or bridge deployments, shared APIs, control planes, caches, and operational tools still require authorization and tenant-context checks.

Treat tenant identity as trusted only after authentication and membership authorization. Never accept a client-supplied tenant ID, document metadata, prompt instruction, or model output as proof of access. Apply the same scope to ingestion, retrieval, cache keys, conversation history, and citation resolution. Test for missing filters, confused-deputy paths, stale ACL metadata, and cross-tenant cache reuse.

### Ingestion and asynchronous re-indexing

1. Store the source object and a durable document record containing tenant ID, immutable document ID, source version, ACL metadata, and desired index generation.
2. Convert storage events into durable queue work. Assume duplicate, delayed, and reordered notifications; use a tenant-scoped idempotency key and persist job state. Parse event schema defensively and route poison work to a dead-letter/reconciliation path. S3 documents at-least-once delivery and possible delay ([Amazon S3 Event Notifications](https://docs.aws.amazon.com/zh_cn/AmazonS3/latest/userguide/EventNotifications.html)).
3. Fetch the exact object version identified by the event when versioning is available. AWS documents that notifications may be out of order and that sequencers can order PUT/DELETE events only for the same object key; compare sequencers as hexadecimal values after left-padding the shorter value with zeros. Do not compare sequencers across different keys ([S3 event message structure](https://docs.aws.amazon.com/AmazonS3/latest/userguide/notification-content-structure.html)).
4. Parse, chunk, and embed into a new, non-searchable generation. Each chunk should retain tenant ID, document/version ID, chunk ID, ACL attributes, and source location (for example page/section or character offsets).
5. Commit all chunks and metadata, then atomically mark the generation current. Retrieval should only see the current complete generation. On deletion, write a tombstone/current-state marker and prevent delayed jobs from resurrecting the document; separately apply retention and physical purge policy. Tombstones prevent logical resurrection but do not themselves prove physical erasure or satisfy retention obligations. Authorize deletion and purge operations against tenant and document policy, and audit them.
6. Reconcile object/document state against index state periodically to repair failed or missed work. Expose indexing status and last successful generation to operators and, where appropriate, users.

This design accepts eventual consistency while preventing partial generations and stale events from silently becoming current. The cited S3 documentation does not guarantee a maximum notification delay or exactly-once processing, so freshness objectives and reconciliation intervals must be set by the service operator.

### Retrieval, context construction, and citations

For each query, derive tenant scope from the authenticated principal and evaluate current document ACLs. Apply mandatory tenant and ACL predicates inside the retrieval operation (or use a tenant-isolated store plus document authorization). OpenAI's Retrieval guide documents metadata filters and compound predicates for vector-store search, but does not establish them as an authorization system ([OpenAI Retrieval guide](https://developers.openai.com/api/docs/guides/retrieval.md)). Do not retrieve broadly and attempt to remove unauthorized content after generation: once content enters model context, it may influence the answer even if later hidden.

The context builder should accept only authorized retrieval records and preserve their provenance. A citation record should bind the response to the request's authorized result set and include tenant scope, immutable document/version ID, chunk ID, source span, and the supporting text or a stable reference to it. Validate that every emitted citation resolves to a retrieved, authorized record; citation resolution itself must re-check tenant and document authorization rather than expose a source through an unguarded lookup. If evidence is insufficient, the response should say so rather than fabricate a citation. The Retrieval guide shows file identifiers and returned content, but does not define a complete ACL system, stable chunk IDs, or source offsets; those are application responsibilities.

### Trade-offs and suitable scenarios

- **Silo:** stronger resource separation and potentially smaller shared-data blast radius; higher per-tenant resource and operational overhead. Still requires shared-plane authorization.
- **Pool:** efficient shared operations and flexible scaling; a missing or mutable filter can create broad cross-tenant exposure. Requires strong policy enforcement, tests, and observability.
- **Bridge:** adapts isolation to tenant/component needs; adds complexity at transitions and requires consistent identity and policy propagation.
- **Asynchronous indexing:** decouples uploads from expensive parsing/embedding and supports retries; introduces freshness lag, duplicate/reordering handling, and reconciliation work.
- **Metadata-filtered retrieval:** flexible and useful for shared indexes; correctness depends on trusted metadata and mandatory server-side filter construction. It is not, by itself, proof of authorization.
- **Evidence-bound citations:** improve auditability and user verification; require preserving source locations and validating citation membership, which adds ingestion and response-path metadata work.

## Recommendations

1. Adopt a **layered reference design**: authenticated identity and tenant membership; explicit tenant/document policy evaluation; tenant-scoped durable ingestion jobs; version-aware, idempotent indexing; mandatory pre-context retrieval authorization; and validated citations.
2. Select silo, pool, or bridge per tenant and component risk, compliance, and operating constraints. Document the boundary and threat model for every shared component and transition.
3. Make tenant scope immutable in server-side request/job context. Include it in storage/index records and cache keys; reject requests or jobs with missing or inconsistent scope.
4. Treat event notifications as triggers, not the source of truth. Maintain desired/indexed state, deduplicate work, guard against stale versions, use tombstones for deletion, and reconcile periodically.
5. Publish re-indexed content by complete generation, not by in-place partial replacement. Keep the previous generation available until the new one is complete, then switch atomically where the chosen store supports it.
6. Enforce tenant and document ACL predicates before model context construction. Add negative tests for cross-tenant retrieval, missing filters, stale ACLs, deletion races, cache collisions, and citation spoofing.
7. Preserve immutable source/version/chunk identifiers and source spans at ingestion. Validate every citation against the authorized retrieval set and retain audit records sufficient to reproduce which evidence supported an answer.
8. Authorize citation resolution, deletion, and physical purge paths independently; record audit events and define retention/erasure semantics. A logical tombstone is not equivalent to physical deletion.
9. Define operational objectives for indexing freshness, retry limits, dead-letter handling, reconciliation, deletion/purge, and audit retention. The available sources do not prescribe these values.

## Limitations

The evidence consists of AWS SaaS Lens and S3 documentation plus the OpenAI Retrieval guide. These sources establish isolation patterns, S3 event behavior, and retrieval filter capabilities, but do not prescribe a complete RAG implementation. Recommendations such as exact-version reads, tombstones, atomic index generations, reconciliation, and citation validation are architectural deductions rather than guarantees of those services. No workload size, tenant count, compliance profile, latency target, cost data, or measured failure rates were provided, so the report cannot quantify the best isolation pattern or operational overhead. The retrieval guide does not establish metadata filters as an authorization boundary or specify stable chunk IDs/source offsets; validate these details against the selected storage and vector-search implementation.

## References

1. [Tenant Isolation - AWS SaaS Lens](https://docs.aws.amazon.com/wellarchitected/latest/saas-lens/tenant-isolation.html)
2. [Silo, Pool, and Bridge Models - AWS SaaS Lens](https://docs.aws.amazon.com/wellarchitected/latest/saas-lens/silo-pool-and-bridge-models.html)
3. [Amazon S3 Event Notifications](https://docs.aws.amazon.com/zh_cn/AmazonS3/latest/userguide/EventNotifications.html)
4. [Amazon S3 Event Message Structure](https://docs.aws.amazon.com/AmazonS3/latest/userguide/notification-content-structure.html)
5. [OpenAI Retrieval Guide](https://developers.openai.com/api/docs/guides/retrieval.md)
