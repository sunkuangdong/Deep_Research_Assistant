# Reference Architecture for a Multi-Tenant RAG Service

## Background

A multi-tenant retrieval-augmented generation (RAG) service must do more than separate customer records in a database. It must preserve authorization from document intake through chunking, indexing, retrieval, generation, and citation rendering. A shared vector index can be operationally efficient, but it makes tenant and principal filtering, identity propagation, and failure handling explicit security requirements. The architecture below is a reference design, not a product-specific deployment prescription.

## Key Findings

1. **Use layered authorization, not a single tenant filter.** Derive tenant context from authenticated identity, authorize at resource boundaries, apply retrieval-time filters on every query, and use database row-level security (RLS) for relational tenant data where appropriate. NIST's zero-trust principles support resource-focused authorization rather than implicit trust based on network location. PostgreSQL RLS can provide default-deny row access when enabled without an applicable policy, but privileged roles and table owners can bypass it under documented conditions.
2. **Treat retrieval filtering as a security control that must be consistently enforced.** Azure AI Search's security-trimming pattern applies principal filters to each query and warns that a principal identifier alone is not authentication or authorization. A hidden/non-retrievable field is not a security boundary.
3. **Keep citation provenance separate from retrieval eligibility.** Preserve stable document and chunk identifiers plus source metadata through retrieval and generation. Return citations only for authorized passages actually used. The available OpenAI retrieval evidence does not establish a complete citation contract, so this should be an application-level invariant.
4. **Make re-indexing asynchronous, idempotent, and observable.** Queue-based workers decouple ingestion from indexing. Amazon SQS provides at-least-once delivery, not exactly-once processing; workers must tolerate duplicates, manage visibility timeouts, and route persistent failures to a dead-letter queue (DLQ).
5. **Define freshness and cutover semantics explicitly.** Incremental updates can be useful for routine changes, but the reviewed evidence does not establish atomic replacement or immediate consistency. Versioning, reconciliation, and acceptable stale-data windows must be designed and tested.

## Evidence and Analysis

### Reference architecture

```text
Client
  │ authenticated request
  ▼
API gateway / identity middleware
  │ verified subject + authorized tenant context
  ▼
RAG orchestration service ───────────────► Authorization/policy service
  │                                          (tenant, group, document ACLs)
  ├── query embedding                         │ authorized principal set
  ├── retrieval query + mandatory filters ◄───┘
  │
  ▼
Vector/search index ── authorized chunks + stable source metadata
  │
  ▼
Context assembly → generation → citation validation/rendering

Document upload/API
  │ authenticate, authorize, validate, malware/content checks
  ▼
Object storage (immutable source/version) + relational metadata/ACLs
  │ transactional outbox or durable job record
  ▼
Queue → idempotent ingestion/index workers → chunk/embed/upsert
  │                                      │
  └── retries / visibility timeout / DLQ └── index version & status
```

The diagram is a recommended composition of controls, not a claim that any one cited product implements the whole architecture.

### 1. Identity, tenant isolation, and data boundaries

The API layer should authenticate the caller and derive the tenant context from verified identity and authorization state. Do not treat a tenant ID supplied in a request body or query string as proof of access. Propagate the authorized context to retrieval, metadata storage, and ingestion operations, and re-check authorization at resource boundaries. This is an architectural application of NIST SP 800-207's resource-focused zero-trust principles, not a RAG-specific prescription ([NIST SP 800-207](https://csrc.nist.gov/pubs/sp/800/207/final)).

For relational metadata—document ownership, ACLs, ingestion status, and job state—PostgreSQL RLS can add a database enforcement layer. Policies should be tested for reads and writes, role scope, and composition. PostgreSQL documents that superusers and `BYPASSRLS` roles bypass RLS, table owners normally bypass it unless `FORCE ROW LEVEL SECURITY` is used, and permissive policies combine with OR. Keep privileged roles out of ordinary request paths and do not assume RLS protects a separate vector index ([PostgreSQL Row Security Policies](https://www.postgresql.org/docs/current/ddl-rowsecurity.html)).

### 2. Document ingestion and asynchronous re-indexing

Represent each source document with a stable document ID, tenant ID, source version, ACL/principal metadata, content hash, ingestion status, and timestamps. Store the original object separately from derived chunks. An ingestion request should authenticate and authorize the uploader, validate file type and size, record a durable job/version, and enqueue work rather than holding the client request open for parsing, chunking, embedding, and indexing.

Workers should be idempotent: a repeated job for the same document version should converge on the same index state rather than create duplicate or mixed chunks. Use explicit job states and retry classification; send persistent failures to a DLQ with enough metadata for safe replay. SQS visibility timeout temporarily hides a received message, but standard queues are at-least-once and can redeliver; visibility timeout is not an exactly-once guarantee. Set or extend it to fit variable job duration and make duplicate processing safe ([Amazon SQS visibility timeout](https://docs.aws.amazon.com/AWSSimpleQueueService/latest/SQSDeveloperGuide/sqs-visibility-timeout.html)).

For updates, use versioned indexing or a controlled replacement/cutover strategy if users must not see a mixture of old and new chunks. The reviewed Azure documentation describes incremental `merge`/`mergeOrUpload` updates keyed by document ID, but does not establish atomic replacement, queue semantics, or freshness guarantees. Define a freshness objective and reconciliation process rather than assuming an update is immediately visible ([Azure AI Search security trimming](https://learn.microsoft.com/en-us/azure/search/search-security-trimming-for-azure-search)).

### 3. Retrieval-time access control and filtering

Before querying the index, resolve the caller's authorized tenant and principal/group set. Apply mandatory tenant and ACL filters to every retrieval request, including follow-up, retry, and tool-generated queries. The filter must be constructed by trusted service code, not accepted as an arbitrary caller-supplied expression. If permissions change, update or invalidate indexed ACL metadata and define how stale permissions are handled.

Azure AI Search documents a security-filter pattern that stores principal identifiers in a filterable field and applies a filter on each query. It explicitly cautions that the principal string is not itself authentication or authorization and that `retrievable: false` is not a security boundary. OpenAI's Retrieval guide describes vector-store search and metadata filters, but the retrieved evidence is insufficient to claim equivalent enforcement guarantees across products ([Azure AI Search security trimming](https://learn.microsoft.com/en-us/azure/search/search-security-trimming-for-azure-search); [OpenAI Retrieval](https://developers.openai.com/api/docs/guides/retrieval)).

A shared index with mandatory filters can be appropriate when tenant scale and operational simplicity favor shared infrastructure, provided filter omission is prevented by a centralized retrieval layer and tested. Separate indexes or storage partitions may reduce blast radius or simplify tenant-specific operations, but introduce additional provisioning and lifecycle complexity; the available evidence does not quantify that trade-off. Choose isolation granularity based on threat model, regulatory requirements, scale, and operational capacity.

### 4. Citations and answer provenance

Carry source identity alongside every chunk: tenant/document ID, source version, page/section or byte offsets where available, and a display-safe source label. The retrieval result should retain these fields through context assembly. After generation, validate that each citation maps to a retrieved passage included in the model context and remains authorized for the requesting user. Render citations from trusted metadata rather than model-invented URLs or titles. Do not expose unauthorized document names or metadata even when the answer text itself appears harmless.

This is an application-level design recommendation. The available OpenAI retrieval excerpt does not verify a complete citation contract, and the other reviewed sources do not specify citation rendering behavior. Therefore, citation correctness and authorization must be enforced and tested by the service.

### 5. Operational controls and failure tests

Instrument ingestion and retrieval with tenant-scoped audit events, job/version status, retry counts, index freshness, filter application, and citation validation outcomes. Avoid logging raw sensitive content unless necessary and governed. Test at minimum: cross-tenant retrieval attempts; missing or malformed filters; stale ACL metadata; RLS bypass roles and policy composition; duplicate queue delivery; worker interruption and replay; DLQ recovery; partial index updates; and citations that do not correspond to authorized retrieved passages.

### Trade-offs and suitable scenarios

- **Layered controls** are suitable when tenant data spans both a vector index and relational metadata. They reduce reliance on any single enforcement point, but require consistent identity propagation and end-to-end tests.
- **Shared index plus query filters** can simplify operations and support shared capacity. Its main risk is a missed or incorrectly constructed filter; centralize query construction and fail closed.
- **Tenant-specific indexes/partitions** may be preferable for stronger isolation or tenant-specific lifecycle needs, but the evidence reviewed here does not establish their cost or performance trade-offs.
- **Asynchronous re-indexing** suits variable-duration work and eventual consistency. It requires idempotency, retry/DLQ operations, freshness monitoring, and explicit version cutover behavior.
- **Citation metadata preservation** is essential where users need auditability or source inspection, but it adds schema and validation responsibilities and does not replace access control.

## Recommendations

1. **Establish a trusted authorization context.** Authenticate the subject, resolve tenant and document permissions server-side, and propagate only verified context. Fail closed when identity or policy resolution is unavailable.
2. **Centralize retrieval construction.** Provide one service path that always injects tenant and principal filters; prohibit unfiltered index access from application handlers. Add negative tests for every retrieval route.
3. **Use defense in depth.** Apply RLS to relational tenant records where suitable, with least-privilege roles, reviewed policy composition, and explicit handling of owner/bypass roles. Treat index filtering as a separate enforcement boundary.
4. **Build a durable, idempotent ingestion pipeline.** Persist source versions and job state, enqueue work, make worker operations repeatable, configure visibility timeouts for job duration, and use a DLQ plus replay/runbook process.
5. **Define index consistency behavior.** Specify acceptable freshness, permission-revocation propagation, update atomicity, and rollback/reconciliation. Use versioned builds and controlled cutover when mixed versions are unacceptable.
6. **Make citations verifiable.** Preserve stable source/chunk identifiers and provenance metadata; validate citations against retrieved, authorized context before returning an answer.
7. **Measure and test security and freshness.** Track filter enforcement, cross-tenant denial tests, ingestion lag, re-index failures, DLQ depth, stale ACL exposure risk, and citation validation failures.

## Limitations

The evidence base contains five distinct official pages: NIST SP 800-207, PostgreSQL row security, Azure AI Search security trimming, OpenAI Retrieval, and Amazon SQS visibility timeout. It supports the principles and product behaviors cited above, but does not provide a complete end-to-end RAG reference implementation or comparative performance/cost data. The OpenAI retrieval page evidence was limited, so exact lifecycle and citation behavior remain incompletely verified. The sources do not specify a complete identity-token protocol, atomic index replacement, freshness SLA, application retry/backoff policy, or a particular tenant isolation topology. No workload, compliance regime, latency target, or scale assumptions were supplied; those inputs are needed to select concrete products and configuration values.

**Sources:** [NIST SP 800-207, Zero Trust Architecture](https://csrc.nist.gov/pubs/sp/800/207/final); [PostgreSQL Row Security Policies](https://www.postgresql.org/docs/current/ddl-rowsecurity.html); [Azure AI Search security trimming](https://learn.microsoft.com/en-us/azure/search/search-security-trimming-for-azure-search); [OpenAI Retrieval](https://developers.openai.com/api/docs/guides/retrieval); [Amazon SQS visibility timeout](https://docs.aws.amazon.com/AWSSimpleQueueService/latest/SQSDeveloperGuide/sqs-visibility-timeout.html).
