# Reliable Asynchronous Image-Generation Workflows: Architecture Research Report

## Background

An image-generation request crosses several independently failing boundaries: a client-facing API, an external model provider, object storage for generated artifacts, and a relational database for job state and metadata. The request may outlive an HTTP connection, provider calls may be slow or ambiguous after timeouts, and artifact persistence may succeed or fail independently of database updates. A reliable design therefore needs explicit acceptance, durable progress tracking, retry semantics, and recovery behavior rather than treating generation as one synchronous request.

The evidence gathered here directly supports API idempotency and HTTP semantics, durable workflow Activities and retries, and saga trade-offs. It does **not** establish object-storage or relational-database guarantees; recommendations for those boundaries are identified as design requirements requiring validation against the selected products.

## Key Findings

1. **Accept asynchronously and expose a status resource.** HTTP `202 Accepted` means processing has not completed; RFC 9110 says the response ought to describe current status and point to or embed a status monitor. It does not guarantee eventual completion. A submission endpoint should return a durable job identifier or status URI and avoid implying that the image is ready. [RFC 9110](https://www.rfc-editor.org/rfc/rfc9110.html)
2. **Make submission retries explicitly idempotent.** POST is not inherently idempotent, so a client retry after a lost response can create duplicate jobs unless the API defines deduplication. AWS's idempotency guidance describes stable client tokens, same-parameter retries returning the original result, and conflicts when a token is reused with changed parameters. Apply this as an API design pattern, not as an image-generation-specific AWS guarantee. [AWS idempotency guidance](https://docs.aws.amazon.com/fr_fr/ebs/latest/userguide/ebs-direct-api-idempotency.html)
3. **Isolate provider calls in durable workflow Activities.** Temporal recommends Activities for failure-prone external calls. Activity retries can use exponential backoff, but defaults include unlimited attempts unless constrained; total retry duration should be bounded with workflow or Activity timeouts. Long-running attempts restart from their initial state unless heartbeat details checkpoint progress. [Temporal Activities](https://docs.temporal.io/activities) · [Temporal Retry Policies](https://docs.temporal.io/encyclopedia/retry-policies)
4. **Treat provider timeouts as potentially ambiguous.** A lost response does not prove the provider failed to generate. Blind retries may duplicate work or charges; refusing retries may leave jobs unresolved. Provider idempotency, status lookup, cancellation, and billing behavior must be verified before choosing a retry/reconciliation policy.
5. **Use saga compensation selectively.** Saga orchestration sequences local transactions and may invoke compensating actions in reverse order. It provides eventual rather than strong consistency and adds complexity and latency. A completed model generation may be irreversible, so compensation may mean cleanup, cancellation where supported, or recording failure—not literal rollback. [AWS Saga Orchestration](https://docs.aws.amazon.com/prescriptive-guidance/latest/cloud-design-patterns/saga-orchestration.html)
6. **Storage and database coordination remain evidence gaps.** The available sources do not establish object durability/consistency, upload completion semantics, relational transaction boundaries, or a transactional-outbox implementation. These must be designed and validated separately; no specific storage/database guarantee is asserted here.

## Evidence and Analysis

### End-to-end pattern

A practical architecture separates the workflow into explicit boundaries:

1. **Submission:** The API validates the request and accepts it with a stable idempotency key. Persist or otherwise durably establish the job identity before acknowledging acceptance. Return `202` with a job ID/status URI. The persistence ordering is a design inference; the cited HTTP standard does not prescribe database implementation.
2. **Observation:** A status endpoint exposes documented states such as queued, running, succeeded, and failed, plus terminal result or error details. GET is safe and idempotent under RFC 9110, making it suitable for repeatable polling. The standard does not prescribe state names, polling intervals, or result schema.
3. **Provider execution:** A durable orchestrator invokes the model provider in an Activity or equivalent isolated step. Classify errors, set attempt and total-duration limits, and separate provider submission from waiting/polling or later processing when their recovery needs differ.
4. **Artifact persistence and completion:** Store the generated image and update job metadata/status as separate side-effect boundaries. Define when the job may be marked successful—for example, only after the required artifact is available and its reference is recorded. This is an architectural recommendation, not a guarantee supported by the current storage/database evidence.
5. **Recovery:** Handle transient failures with bounded retries; handle ambiguous provider outcomes through provider status reconciliation, idempotent provider requests if supported, or an explicit manual/operational resolution path. Use compensations only for steps with meaningful compensating actions.

### Comparison and trade-offs

| Concern | Pattern | Benefit | Trade-off / caveat |
|---|---|---|---|
| Client retry after uncertain submission | Idempotency key bound to one logical request and its parameters | Prevents duplicate job creation when clients retry | Key scope, retention, concurrent duplicate behavior, and changed-payload response must be specified by the API |
| Long-running request visibility | `202` plus durable status resource | Decouples client connection lifetime from generation and supports progress observation | Acceptance is not completion; polling cadence and terminal-state semantics are service-specific |
| Provider failures | Durable Activity with classified, bounded retries and timeouts | Recovers transient failures and isolates external calls | Retry may duplicate provider work if the provider completed but the response was lost |
| Multi-step side effects | Saga orchestration with compensations | Coordinates independently committed steps and provides a recovery path | Eventual consistency, added latency/complexity, and some actions may be irreversible |
| Artifact and job-state consistency | Explicit storage and database stages with recovery rules | Makes partial completion visible and recoverable | Current evidence does not validate any particular transaction, object-store, or outbox mechanism |

API idempotency and workflow retries solve different problems: the former deduplicates client submissions; the latter retries internal work. Neither alone guarantees exactly-once provider execution. Likewise, a status endpoint improves observability but does not itself ensure eventual completion. The strongest design is explicit about these boundaries and avoids claiming exactly-once behavior unless the provider and persistence contracts support it.

### Suitable scenarios

- Use idempotency keys and a status resource whenever clients may retry submissions or generation outlives a normal request-response window.
- Use durable orchestration with bounded retries when provider calls are transiently fallible, long-running, or need operational visibility.
- Split work into stages when provider submission, waiting, artifact handling, and final status updates have different timeouts or recovery behavior.
- Use saga orchestration when multiple independently committed steps have meaningful compensations; it may be unnecessary for a single irreversible provider call with no useful rollback.
- Use reconciliation or manual review as a fallback when provider completion is ambiguous and duplicate execution is costly.

## Recommendations

1. **Define the API contract first:** return `202` with a stable job ID/status URI; document lifecycle states, terminal errors/results, polling guidance, and idempotency-key scope, retention, payload binding, and conflict behavior.
2. **Persist a durable job record and make transitions explicit:** model submission, provider execution, artifact persistence, and terminal status as observable stages. Ensure retries cannot silently create a second logical job.
3. **Use a durable orchestrator for provider work:** isolate provider calls in Activities or equivalent units; classify retryable versus non-retryable errors; set explicit attempt and total-duration limits; checkpoint long-running work where supported.
4. **Design for ambiguous provider outcomes:** verify provider idempotency, request lookup, cancellation, and billing semantics. If unavailable, define bounded retry and reconciliation/manual-review rules rather than assuming retries are harmless.
5. **Treat object storage and the relational database as separate failure boundaries:** specify artifact naming/immutability, upload completion verification, cleanup, job-state transition rules, and recovery for partial success. Select and validate a transaction/outbox or reconciliation approach against the actual database and object-store documentation; the current evidence does not justify prescribing one.
6. **Use saga compensation only where it is real:** document each compensating action and its limits. Do not describe irreversible provider work as rolled back.
7. **Instrument operational outcomes:** track queue age, stage duration, retry counts, provider ambiguity, artifact persistence failures, and jobs stuck outside terminal states. These are implementation recommendations, not metrics prescribed by the cited sources.

## Limitations

- The evidence set contains five distinct eligible pages, but only API semantics, idempotency, Temporal Activities/retries, and AWS saga guidance are directly covered.
- No official object-storage or relational-database source was preserved in the findings. Consequently, this report does not claim specific durability, consistency, transaction, locking, or outbox guarantees; those require additional product-specific research.
- No model-provider documentation was available. Provider idempotency, status lookup, cancellation, timeout behavior, and duplicate billing remain uncertain and materially affect safe retry policy.
- The AWS idempotency page is French-localized and notes that English prevails in case of translation conflict. Its token behavior is used as general design guidance, not as an image-generation API specification.
- RFC 9110 does not define a universal asynchronous job schema, state vocabulary, polling interval, or eventual-completion guarantee. Temporal and AWS guidance is general-purpose rather than image-generation-specific.
- No image-generation-specific timeout values, retry budgets, polling intervals, or storage/database ordering guarantees are established.

### References

1. [RFC 9110: HTTP Semantics](https://www.rfc-editor.org/rfc/rfc9110.html)
2. [AWS EBS idempotency guidance](https://docs.aws.amazon.com/fr_fr/ebs/latest/userguide/ebs-direct-api-idempotency.html)
3. [Temporal Activities](https://docs.temporal.io/activities)
4. [Temporal Retry Policies](https://docs.temporal.io/encyclopedia/retry-policies)
5. [AWS Saga orchestration pattern](https://docs.aws.amazon.com/prescriptive-guidance/latest/cloud-design-patterns/saga-orchestration.html)

**Evidence inventory:** 5 distinct eligible source pages preserved in the findings/analysis for this run.