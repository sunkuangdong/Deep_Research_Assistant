# Reliable Asynchronous Image-Generation Workflows: Architectural Research Report

## Background

Image generation is often too slow or variable to fit safely inside a single client-facing request. A robust design therefore separates request acceptance from execution and result retrieval, while coordinating four independently failing components: the API, model provider, object storage, and relational database. The central architectural challenge is not merely moving work to a queue; it is preserving a coherent job identity and recoverable state when clients retry, workers crash, provider responses time out, or artifact publication and database updates complete at different times.

The evidence collected here directly documents retry/idempotency principles, Amazon SQS delivery and visibility behavior, Amazon S3 read-after-write consistency, and Google Cloud Storage conditional request preconditions. It does not directly document a particular model provider's guarantees or a relational database's transaction/outbox behavior. Recommendations for those components are therefore identified as architectural design implications rather than provider-specific guarantees.

## Key Findings

1. **Design for at-least-once execution, not end-to-end exactly-once processing.** Amazon SQS standard queues can deliver a message more than once, including during a visibility timeout. A worker may also finish work but fail before acknowledging the message. Stable job identity and duplicate-safe state transitions and publication are therefore essential. [Amazon SQS visibility timeout](https://docs.aws.amazon.com/AWSSimpleQueueService/latest/SQSDeveloperGuide/sqs-visibility-timeout.html)

2. **Make submission retries idempotent and expose a durable job resource.** A client may time out after the server has accepted a request. An idempotency key associated with the request intent can make a retry resolve to the same logical job rather than create another generation. Return a stable job identifier and expose status/result separately from submission. This applies the high-level retry-safety principle in [AWS Builders' Library](https://aws.amazon.com/builders-library/making-retries-safe-with-idempotent-APIs/); key scope, conflict behavior, and retention must be explicitly designed.

3. **Treat queue visibility and retry policy as workload-specific recovery controls.** A visibility timeout that is too short can cause concurrent duplicate work; one that is too long delays recovery after a worker crash. For variable-duration jobs, extend visibility while processing and acknowledge only after required durable completion. Bound repeated failures with a dead-letter queue and an intentional redrive policy. [SQS visibility timeout](https://docs.aws.amazon.com/AWSSimpleQueueService/latest/SQSDeveloperGuide/sqs-visibility-timeout.html) and [SQS dead-letter queues](https://docs.aws.amazon.com/AWSSimpleQueueService/latest/SQSDeveloperGuide/sqs-dead-letter-queues.html) document these component-level mechanisms, but do not prescribe universal timeout or retry values.

4. **Publish the image before marking the job successful, while planning for partial completion.** Amazon S3 documents strong read-after-write consistency for object PUT and DELETE operations, so a successfully written object can be read without an application-added visibility delay. Google Cloud Storage request preconditions can guard operations against unexpected object generations and races. Neither storage guarantee makes an object write atomic with a relational database update. [Amazon S3 User Guide](https://docs.aws.amazon.com/AmazonS3/latest/userguide/Welcome.html); [Google Cloud Storage request preconditions](https://docs.cloud.google.com/storage/docs/request-preconditions).

5. **Provider calls and relational state need explicit, provider-specific recovery design.** The available evidence does not establish whether a model provider supports idempotency keys, request lookup after timeouts, cancellation, or duplicate-billing protection. Nor does it establish database isolation, transactional outbox, or queue/database atomicity. Do not assume these guarantees; validate them for the selected provider and database.

## Evidence and Analysis

### Recommended end-to-end pattern

A practical workflow can be organized around a durable job record and explicit state transitions:

1. **Accept:** Validate the request and create a job record using a client idempotency key. If the same intent is retried, return the existing job identity. Return promptly with a job identifier and a status/result endpoint rather than holding the API request open for generation.
2. **Dispatch:** Enqueue a reference to the durable job, not the only copy of the request or state. The database/queue coordination mechanism is implementation-specific; the supplied evidence does not establish an atomic transaction spanning them.
3. **Execute:** Workers assume duplicate delivery is possible. Before expensive work, check the job's current state and use guarded transitions so concurrent or repeated deliveries do not blindly create conflicting outcomes. For Amazon SQS, set visibility to cover expected processing and durable completion and extend it for variable-duration work. For other queue products, verify their delivery and acknowledgement guarantees; duplicate-safe handling remains a conservative design assumption. Acknowledge only after the required durable work is complete.
4. **Call the model provider:** Treat a timeout after submission as an ambiguous outcome until provider semantics are known. If the provider offers idempotency or request-status lookup, use it; otherwise define a cautious retry and reconciliation policy that accounts for duplicate generation and cost.
5. **Publish:** Write the generated image to object storage using a deliberate key/version strategy. Use conditional writes where concurrent replacement or duplicate publication is a concern. Record the object key and relevant metadata in the job record.
6. **Complete:** Mark the job successful only after the artifact is durably available and its reference is recorded. Since storage and database updates are separate operations, provide reconciliation for states such as “object exists, job still running” and “job failed, artifact exists.”
7. **Recover and operate:** Bound retries, route persistent failures to a dead-letter queue, and provide diagnosis/redrive procedures. Monitor both visible backlog and in-flight work; long-running jobs can consume in-flight capacity even when the visible queue is small.

### Component trade-offs and failure modes

| Component | Reliability mechanism | Trade-off / failure mode | Evidence status |
|---|---|---|---|
| API and job identity | Idempotency key, stable job ID, explicit status resource | Key reuse, retention, and request-equivalence rules require policy; without deduplication, ambiguous client timeouts can create duplicate jobs | High-level retry/idempotency principle documented; detailed job schema is an architectural application |
| Queue and workers | Visibility timeout, heartbeat extension, bounded retries, DLQ | Short timeout risks concurrent duplicate work; long timeout delays recovery; poison jobs need inspection and redrive | SQS-specific behavior documented; values depend on workload |
| Model provider | Provider idempotency or request reconciliation where available | Ambiguous timeout may lead to duplicate generation, cost, or inconsistent results | Not established by the collected sources; verify provider documentation |
| Object storage | Write artifact before success; conditional writes/versioning where needed | Object write and database update are not atomic; partial completion requires reconciliation | S3 consistency and GCS preconditions documented; cross-system atomicity is not |
| Relational database | Durable job state and guarded transitions; consider an outbox/reconciliation design | Database transaction alone cannot atomically include provider calls, object writes, or queue acknowledgement | Database-specific guarantees were not researched in the preserved evidence; validate chosen implementation |

**Illustrative recovery case (design example, not a provider guarantee):** a worker writes an image successfully, then crashes before updating the relational job row or acknowledging the queue message. On redelivery, the next worker checks the job state and deterministic job/artifact identity, verifies whether the expected object already exists, and completes or reconciles the database transition rather than blindly publishing a conflicting result. Conversely, if the database update fails after the object write, a reconciliation process can detect the artifact-present/nonterminal-job state and safely finish the transition or flag it for review.

The strongest evidence supports component-level guarantees, not a global exactly-once transaction. Reliability comes from combining durable identity, idempotent application behavior, explicit state transitions, bounded retries, and reconciliation. A relational database is a reasonable candidate for authoritative job state, but that is an architectural choice here, not a conclusion established by the collected database documentation.

## Recommendations

- Use an asynchronous job API: accept quickly, return a stable job ID, and provide a status/result resource.
- Require or generate an idempotency key for submission; define request equivalence, conflicting key reuse, and retention explicitly.
- For Amazon SQS standard queues, treat delivery as at-least-once. For other queue products, verify their delivery guarantees and retain duplicate-safe handling as a conservative design assumption. Make state transitions and artifact publication safe under duplicate attempts.
- Tune SQS visibility timeout to the full processing-and-durable-completion interval, extend it for variable work, and acknowledge only after durable completion. Use a bounded retry policy and DLQ with operational redrive procedures.
- Verify model-provider semantics before enabling automatic retries: idempotency, request lookup, timeout behavior, cancellation, rate limits, and billing implications are especially important.
- Write the artifact before exposing success. Use immutable/versioned object keys or conditional writes where concurrent writers or replacement are possible.
- Keep job state and artifact references durable and observable. Add reconciliation for partial states across database, queue, provider, and storage; do not imply that separate component commits are atomic.
- Monitor job age, queue backlog, in-flight work, retry counts, DLQ depth, provider errors/timeouts, artifact-write failures, and jobs stuck in nonterminal states.

## Limitations

The evidence base contains five distinct official documentation pages, but it is uneven across the requested components. Queue behavior is specific to Amazon SQS; storage evidence covers Amazon S3 consistency and Google Cloud Storage preconditions. The API source supports a high-level idempotency principle, while the extracted article content did not verify detailed key-retention or conflict policies. No preserved source directly covers a model provider's image-generation API or relational database transactions/outbox behavior. Consequently, provider and database recommendations are architectural inferences and must be checked against the selected products. No workload measurements were supplied, so timeout, retry, concurrency, and capacity values cannot be sized here.

### References

1. [Making retries safe with idempotent APIs — AWS Builders' Library](https://aws.amazon.com/builders-library/making-retries-safe-with-idempotent-APIs/)
2. [Amazon SQS visibility timeout](https://docs.aws.amazon.com/AWSSimpleQueueService/latest/SQSDeveloperGuide/sqs-visibility-timeout.html)
3. [Using dead-letter queues in Amazon SQS](https://docs.aws.amazon.com/AWSSimpleQueueService/latest/SQSDeveloperGuide/sqs-dead-letter-queues.html)
4. [What is Amazon S3? — Amazon S3 User Guide](https://docs.aws.amazon.com/AmazonS3/latest/userguide/Welcome.html)
5. [Request preconditions — Google Cloud Storage documentation](https://docs.cloud.google.com/storage/docs/request-preconditions)
