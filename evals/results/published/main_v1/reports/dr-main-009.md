# Reliable Asynchronous Image-Generation Workflows

## Background

An image-generation request crosses several independently failing systems: a client-facing API, a relational database, a queue or dispatcher, an external model provider, and object storage. No single transaction normally spans all of them. A client timeout may leave the API unsure whether a request was committed; a worker may crash after the provider completed; an image may upload successfully while its database record fails to commit. Reliability therefore depends on durable state, explicit boundaries, idempotent retries, and reconciliation rather than assuming one end-to-end atomic operation.

This report synthesizes four distinct source pages preserved in the research findings. The requested minimum was five; the available research and delegation budget was exhausted before a fifth relevant page could be added. The report does not claim to meet that source-count threshold. The editor review confirmed that the required headings are exact and that the provider-specific caveat is appropriately prominent; it also noted that the source-count shortfall remains a requirement gap. No additional source could be added within the exhausted search and researcher budgets.

## Key Findings

1. **Make acceptance durable.** Persist a job with a stable identifier and initial state before acknowledging acceptance. Use a client idempotency key so a retry after an ambiguous API timeout can return the existing job rather than create another generation. These are architectural recommendations; the available sources do not establish a general HTTP contract or provider-level exactly-once behavior.
2. **Use a transactional outbox for database-to-queue handoff.** Commit the job row and dispatch event in one relational transaction, then publish the outbox event asynchronously. This addresses the dual-write gap between database commit and message publication. Assume duplicate delivery and make consumers idempotent.
3. **Treat provider retries as endpoint-specific.** The available Google Cloud page concerns online inference for custom-trained models, not asynchronous image generation. It does not establish operation polling, timeout outcomes, idempotency, or duplicate-submission guarantees. A timeout must not be interpreted as proof that the provider did not accept the request.
4. **Publish artifacts only after upload and verification.** Upload to a unique or immutable object key, verify the write and expected properties, then commit the image metadata and job completion in one database transaction. Persist object key and, where applicable, version ID and checksum. This avoids exposing a database reference before the artifact is available, but can leave an orphaned object if the database commit fails.
5. **Build recovery around explicit failure windows.** Retain/retry outbox events, guard state transitions, record attempts, reconcile ambiguous provider calls where supported, and clean up orphans after a retention period. Object versioning can aid recovery from overwrite or deletion, but does not coordinate object storage with database transactions.

## Evidence and Analysis

### Durable job and dispatch

The AWS transactional outbox guidance describes the dual-write problem: a database update and event publication can fail independently. Writing the job and outbox event in the same transaction ensures the publisher sees only committed work; a separate publisher or CDC process can retry delivery. The same findings note duplicate delivery and the need for idempotent consumers. This pattern is most useful when losing an accepted job or dispatching an event for rolled-back work is unacceptable. It adds an outbox publisher/CDC path and operational monitoring, but makes the handoff recoverable. Source: [AWS Prescriptive Guidance — Transactional outbox pattern](https://docs.aws.amazon.com/prescriptive-guidance/latest/cloud-design-patterns/transactional-outbox.html).

A practical job state machine can include `accepted`, `queued`, `running`, `succeeded`, and `failed`, with optional cancellation states. Conditional transitions, stable event IDs, leases, heartbeats, and attempt records help prevent stale or duplicate workers from overwriting terminal state. These are design recommendations, not a state machine prescribed by the cited AWS page. Queue-level ordering or deduplication does not make external provider calls and storage writes atomic.

### Provider invocation and ambiguous outcomes

The provider findings could not verify image-generation-specific guarantees. The fetched Google Cloud documentation page is about online inference for custom-trained models and does not establish asynchronous image-generation operation handles, polling, idempotency, or retry semantics. Consequently, automatic resubmission after a timeout may duplicate work or charges if the provider accepted the first request. Before enabling retries, verify the exact endpoint's behavior. If the provider offers no safe idempotency mechanism, record an ambiguous attempt and reconcile status where possible rather than blindly resubmitting. Source: [Google Cloud Documentation — Get online inferences from a custom trained model](https://docs.cloud.google.com/gemini-enterprise-agent-platform/machine-learning/predictions/get-online-predictions).

### Artifact and relational metadata consistency

Amazon S3 documents strong read-after-write consistency for object PUT and DELETE operations and relevant metadata reads. S3 versioning can help recover from accidental overwrite or deletion. PostgreSQL transactions provide all-or-nothing behavior for grouped database changes. These guarantees apply within their respective systems; they do not create a transaction spanning S3 and PostgreSQL. Sources: [Amazon S3 consistency documentation](https://docs.aws.amazon.com/AmazonS3/latest/userguide/Welcome.html#ConsistencyModel) and [PostgreSQL — Transactions](https://www.postgresql.org/docs/current/tutorial-transactions.html).

The recommended publication order is therefore: upload the artifact; verify successful completion and expected properties; then commit the image row, object reference, and terminal job state together in the database. Expose the image only after that commit. Upload-first can leave an orphan if the database transaction fails, while database-first can expose a reference to a missing artifact. Reconciliation should retry metadata publication or clean up unreferenced objects, and detect records whose objects are missing or invalid. Persisting an object version identifier and checksum can make references more stable, but these cross-system procedures are derived recommendations rather than a vendor-prescribed protocol.

### Failure-window comparison

| Boundary/failure | Risk | Resilience pattern |
|---|---|---|
| Job committed, event not published | Accepted job stalls | Transactional outbox; retry/CDC and backlog monitoring |
| Duplicate event or worker restart | Duplicate provider work or state overwrite | Idempotent consumer; conditional claim/state transition; attempt tracking |
| Provider timeout | Remote acceptance is unknown | Endpoint-specific reconciliation; avoid blind retry |
| Upload succeeds, DB commit fails | Orphaned object | Idempotent metadata retry or delayed cleanup |
| DB commit succeeds, object later missing/overwritten | Broken or changed artifact reference | Reconciliation; immutable keys/version IDs; repair or regenerate |

The strongest directly supported pattern is the outbox for the database-to-event boundary, paired with idempotent consumers. For artifact publication, the evidence supports treating object storage and relational metadata as separate consistency domains. Provider invocation remains the largest unresolved uncertainty; exactly-once generation cannot be claimed from the available evidence.

## Recommendations

1. **Define a durable API contract.** Accept a request only after persisting a job ID, request parameters or a durable request reference, initial state, and idempotency key. Return the job resource/status location and make repeated submissions with the same key resolve to the same job. Specify key scope and retention explicitly.
2. **Atomically record work and dispatch intent.** Insert the job and outbox event in one database transaction. Publish asynchronously with retry or CDC. Keep event IDs stable and make consumers safe under at-least-once delivery.
3. **Use guarded, observable job transitions.** Record state, attempt number, timestamps, provider operation/reference when available, and structured error details. Use conditional updates and leases/heartbeats to recover abandoned work without allowing stale workers to overwrite terminal results.
4. **Make provider retry policy conservative and documented.** Verify the exact image endpoint's idempotency, operation-status, timeout, and retry behavior. Distinguish definite failure from ambiguous outcome. Reconcile before resubmitting when possible; do not promise exactly-once generation unless the provider contract supports it.
5. **Upload before publishing metadata.** Use unique or immutable object keys; verify the completed object and expected size/checksum where supported. Then atomically commit metadata and job success in the relational database. Store version identifiers when available and expose only committed records.
6. **Operate reconciliation as a first-class workflow.** Periodically detect stale jobs, unpublished outbox rows, orphaned objects, and metadata pointing to missing objects. Make repair actions idempotent, retain enough attempt history for diagnosis, and alert on age/backlog rather than relying only on request-path retries.

## Limitations

Only four distinct in-run source pages are preserved, below the requested minimum of five. The research/delegation and search budgets were exhausted before a fifth relevant source could be added; no irrelevant links are included to pad the count. The Google Cloud page is not evidence for asynchronous image-generation behavior. No provider-specific image-generation guarantees for polling, idempotency, timeout outcomes, or duplicate submissions were verified. The cited AWS, S3, and PostgreSQL pages establish component-level behaviors, not a complete end-to-end protocol. State-machine details, leases, checksums, cleanup, and reconciliation are recommendations derived from those boundaries and should be validated against the selected provider, queue, storage service, and database.