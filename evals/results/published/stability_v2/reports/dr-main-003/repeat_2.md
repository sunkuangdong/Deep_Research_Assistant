# Redis Streams, RabbitMQ, and Apache Kafka as Event Backbones for Asynchronous AI Jobs

## Background

Asynchronous AI systems commonly separate job submission from execution: an API or workflow service publishes work, workers perform inference or other long-running tasks, and results or status updates are persisted elsewhere. The event backbone must handle worker crashes, bursts, retries, ordering constraints, and backlog growth without implying that broker delivery alone guarantees exactly-once execution of an AI job.

This report compares Redis Streams, RabbitMQ, and Apache Kafka across delivery semantics, ordering, retries and dead-letter handling, scalability, and operational complexity. The evidence collected in this run covers Redis Streams and RabbitMQ only. Kafka is included in the comparison matrix to make the evidence gap explicit, but Kafka-specific behavior and recommendations remain unverified; consequently, this is not a fully evidenced three-way comparison.

## Key Findings

- **Idempotency is essential for reliable job execution.** Redis Streams pending-entry recovery and RabbitMQ redelivery can cause a job to run more than once. Acknowledge only after durable completion or result publication, and use stable job IDs, deduplication, or idempotent side effects.
- **Redis Streams offers a compact, flexible work log, but reliability policy is largely an application responsibility.** Persistence settings, pending-entry recovery, retry/backoff, dead-lettering, and retention need deliberate configuration and operational ownership.
- **RabbitMQ provides explicit queue-oriented acknowledgment and dead-letter mechanisms.** Manual acknowledgments, publisher confirms, prefetch, and bounded retry/DLX patterns support controlled work distribution. Stronger quorum-queue durability and at-least-once dead-lettering add resource, latency, and monitoring costs.
- **Ordering is scoped and can be weakened by parallelism.** Redis stream IDs order appends within a stream; RabbitMQ basic queue order does not guarantee completion order with multiple consumers, requeues, or redeliveries. Strict sequencing requires constrained concurrency or partitioning.
- **A complete three-way recommendation is not supported by this evidence set.** No Kafka findings or eligible Kafka source URLs were collected, and no comparable throughput, latency, or cost benchmarks are available.

## Evidence and Analysis

### Delivery semantics and durability

Redis Streams consumer groups distribute entries among workers and track acknowledgments and pending entries. This supports recovery after a worker failure, but redelivery means processing is at-least-once in practice. Durability depends on Redis persistence configuration: RDB, AOF, both, or no persistence have different recovery and potential data-loss characteristics. A Streams deployment should therefore choose persistence settings against an explicit acceptable job-loss window. See [Redis Streams](https://redis.io/docs/latest/develop/data-types/streams/) and [Redis persistence](https://redis.io/docs/latest/operate/oss_and_stack/management/persistence/).

RabbitMQ separates publisher confirms from consumer acknowledgments: confirms cover broker acceptance, while acknowledgments indicate that a consumer has processed a delivery. Manual acknowledgments allow unacknowledged work to be requeued after a channel or connection failure; this can duplicate execution. Automatic acknowledgment is less protective against loss. Quorum queues provide replicated durability and availability, with consensus-related latency and resource trade-offs. See [Consumer Acknowledgements and Publisher Confirms](https://www.rabbitmq.com/docs/confirms) and [Quorum Queues](https://www.rabbitmq.com/docs/4.2/quorum-queues).

For either system, broker-level delivery is not equivalent to exactly-once execution across model calls, databases, object stores, or external APIs. A robust AI worker should use a stable job identifier, make side effects idempotent where possible, and record completion durably before acknowledging.

### Ordering

Redis stream IDs establish append order within a stream, but parallel workers can complete jobs in a different order. Multiple streams do not create a single global order. RabbitMQ queues are ordered in the basic case, but multiple publishing channels can interleave, and multiple consumers, priorities, requeues, and redeliveries can change observed delivery or completion order. For either broker, strict per-entity sequencing generally requires a single active worker for that sequence or partitioning by entity with controlled concurrency. See [Redis Streams](https://redis.io/docs/latest/develop/data-types/streams/) and [RabbitMQ queues](https://www.rabbitmq.com/docs/queues).

Kafka ordering and partition semantics were not researched in this run; no Kafka ordering claim is made.

### Retries and dead-letter handling

Redis pending-entry tracking can help identify abandoned work and support reclaiming it, but the evidence collected does not establish a complete built-in retry schedule or dead-letter policy. Teams should define bounded attempts, backoff, poison-job handling, and a separate dead-letter stream, preserving the original job ID and failure metadata. Reclaiming work can duplicate execution.

RabbitMQ negative acknowledgments can requeue, discard, or dead-letter a message. Immediate requeue can create hot loops, so retries should be bounded and delayed/backed off. Quorum queues support poison-message handling and redelivery limits. At-least-once dead-lettering is configurable rather than automatic; it can retain messages and consume additional resources, and duplicates may appear at the target. See [RabbitMQ confirms](https://www.rabbitmq.com/docs/confirms) and [RabbitMQ quorum queues](https://www.rabbitmq.com/docs/4.2/quorum-queues).

Kafka retry and dead-letter behavior was not researched and remains unverified.

### Scalability and operational complexity

Redis Streams can distribute work across consumers. For teams already operating Redis, reusing it may reduce the need to introduce a separate broker, but that is a contextual operational judgment rather than a measured complexity ranking. Reliability still requires persistence choices, consumer-group lifecycle management, pending-entry monitoring and recovery, retention controls, idempotency, and application-owned retry/DLQ policy. More streams can increase parallelism but complicate ordering and operations.

RabbitMQ scales work distribution through consumers and queue partitioning. More consumers can increase throughput but weaken observed ordering. Quorum queues add replication and consensus overhead; queue limits, backpressure, and dead-letter capacity need monitoring. Operational work includes confirms, manual acknowledgments, prefetch, retry/backoff, DLX configuration, and backlog/unacknowledged-message monitoring. See [RabbitMQ queues](https://www.rabbitmq.com/docs/queues) and [RabbitMQ quorum queues](https://www.rabbitmq.com/docs/4.2/quorum-queues).

No comparable benchmark evidence was collected, so this report does not rank throughput, latency, or cost. Kafka's scaling model and operational burden cannot be compared from the available findings.

| Dimension | Redis Streams | RabbitMQ | Apache Kafka |
|---|---|---|---|
| Delivery and durability | Consumer-group acknowledgments and pending entries; durability depends on Redis persistence configuration; duplicate processing is possible. | Publisher confirms and consumer acknowledgments; manual ack/requeue supports recovery; quorum queues add replicated durability with overhead. | Not assessed: no Kafka evidence collected. |
| Ordering | Append order within a stream; parallel completion can reorder. | Basic queue order, but concurrency, requeue, and redelivery can affect observed order. | Not assessed. |
| Retries / dead letters | Pending-entry recovery is available; full retry/DLQ policy is application-owned in the evidence reviewed. | Requeue and DLX mechanisms; bounded delayed retries recommended; quorum DLX reliability is configurable with trade-offs. | Not assessed. |
| Scalability | Add consumers; Redis capacity, retention, and stream partitioning constrain design. | Add consumers/queues; partitioning increases parallelism; quorum replication costs resources. | Not assessed. |
| Operational complexity | Context-dependent; reliability requires persistence, recovery, retention, and retry policy ownership. | Context-dependent; stronger guarantees add configuration and monitoring burden. | Not assessed. |

## Recommendations

1. **For teams already operating Redis and seeking a lightweight work-distribution layer:** consider Redis Streams when the team is willing to own persistence configuration, pending-entry recovery, bounded retries, dead-letter streams, retention, and idempotency. “Lightweight” here is a contextual fit judgment, not a measured performance or complexity ranking. Validate version-specific trimming and recovery behavior before production.
2. **For queue-centric workloads needing explicit acknowledgment and routing controls:** consider RabbitMQ. Use publisher confirms, manual acknowledgments, bounded retries with delay/backoff, prefetch appropriate to worker capacity, and monitored dead-letter routing. Consider quorum queues for important durable jobs only after evaluating their latency and resource costs.
3. **For strict ordering:** define the ordering key and scope first. Use constrained concurrency or partitioning so jobs for the same entity are processed serially; do not assume parallel workers preserve completion order.
4. **For all three-way selection decisions:** do not choose Kafka based on this report. Collect Kafka-specific official evidence and benchmark all candidates with representative job payloads, processing-time distributions, failure/retry patterns, retention needs, and recovery objectives.
5. **For AI job correctness:** treat delivery as potentially duplicated, persist job state and results durably, and make external side effects idempotent or deduplicated. Keep large model inputs/outputs in object storage and send references in broker messages where appropriate; this is an architectural recommendation, not a broker-specific guarantee.

## Limitations

- Kafka evidence is absent. Kafka delivery semantics, ordering, retries, dead-letter handling, scalability, and operational complexity are unverified; no Kafka-specific recommendation is supported.
- The evidence inventory contains five distinct eligible official pages, all for Redis or RabbitMQ. It does not provide Kafka coverage, so the requested three-product comparison is incomplete on evidence.
- Redis Streams findings note that the retrieved Streams overview was truncated. Detailed retry, dead-letter, trimming, and consumer-group recovery behavior should be checked against the deployed Redis version.
- RabbitMQ evidence includes current confirms/queues documentation and a quorum-queue page for RabbitMQ 4.2 that the findings identify as no longer actively maintained. Verify exact behavior against the deployed release and client library.
- No workload-specific throughput, latency, cost, or capacity measurements were collected. Performance rankings require representative benchmarking.

## References

Official documentation:

1. [Redis Streams](https://redis.io/docs/latest/develop/data-types/streams/)
2. [Redis persistence](https://redis.io/docs/latest/operate/oss_and_stack/management/persistence/)
3. [RabbitMQ Consumer Acknowledgements and Publisher Confirms](https://www.rabbitmq.com/docs/confirms)
4. [RabbitMQ Queues](https://www.rabbitmq.com/docs/queues)
5. [RabbitMQ Quorum Queues](https://www.rabbitmq.com/docs/4.2/quorum-queues)
