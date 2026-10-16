## Background

Asynchronous AI workloads commonly involve long-running inference, GPU-bound workers, external API calls, retries, and side effects such as writing results or updating job state. An event backbone must therefore do more than accept messages: it must make failure recovery, duplicate execution, ordering scope, retention, and worker concurrency explicit. This report compares Redis Streams, RabbitMQ, and Apache Kafka using the official documentation evidence preserved in this run’s findings. It distinguishes broker delivery from successful end-to-end job completion.

## Key Findings

- **RabbitMQ has the clearest queue-oriented controls in the evidence reviewed.** Manual acknowledgements, publisher confirms, prefetch, and dead-letter exchanges support explicit control over delivery and failure routing. Reliability still depends on correct configuration, especially durable queues plus persistent messages and safe dead-letter forwarding.
- **Redis Streams offers consumer groups and pending-entry recovery, but retry policy and dead-letter workflow are largely application responsibilities.** Redis Cluster can shard and scale, but asynchronous replication means availability should not be mistaken for a guarantee that acknowledged writes cannot be lost.
- **Kafka is a plausible fit for partitioned, replay-oriented workloads, but this run’s Kafka evidence is materially incomplete.** The fetched semantics page did not expose substantive content, and the concepts URL was only a fragment of the same page. Its exact guarantees and configuration-level behavior cannot be confidently compared here.
- **None of the brokers guarantees exactly-once completion of an external AI inference or side effect.** Use idempotency/deduplication, durable job-state transitions, bounded concurrency, and explicit poison-job handling.
- **There is no universal winner.** Choose based on required loss/replay tolerance, ordering scope, retry/DLQ ownership, workload shape, and the team’s operational expertise—not on a generic throughput claim.

## Evidence and Analysis

### Comparative view

| Dimension | Redis Streams | RabbitMQ | Apache Kafka |
|---|---|---|---|
| Delivery semantics | Consumer groups track delivered-but-unacknowledged entries as pending; `XACK` acknowledges. Pending entries can be inspected and reclaimed, which can cause redelivery. Redis Cluster’s asynchronous replication can lose acknowledged writes in some failure scenarios. | Manual consumer acknowledgements allow acknowledgement after processing; unacknowledged deliveries can be requeued after channel/connection closure. Publisher confirms cover the separate publisher-to-broker boundary. Durable queues and persistent messages are both needed for restart recovery. | Findings describe delivery guarantees and transactional processing as requiring explicit design, but the fetched semantics page did not provide substantive text to verify exact guarantees. Delivery does not itself ensure exactly-once execution of external model calls or side effects. |
| Ordering | Stream IDs establish entry order. Concurrent consumers and recovery can make completion order differ from entry order. | FIFO behavior can be affected by priorities, multiple consumers, and redelivery/requeue. A single active consumer is the cited approach when strict queue order is needed. | **Provisional:** findings describe ordering as partition-scoped, not global, but this was not independently verified from substantive Kafka documentation in this run. |
| Retries | Pending-entry inspection and reclaim support recovery; schedules, attempt limits, and backoff are application policies. | Negative acknowledgement/requeue can redeliver. TTL/delay routing back to work is a possible pattern, not a universal retry policy. Prefetch bounds in-flight deliveries. | Bounded retries with backoff and retry topics are application-level patterns in the findings, not verified guarantees. Retry topics can alter effective ordering and add operational burden. |
| Dead-letter handling | The cited evidence does not establish an automatic retry schedule or built-in DLQ policy. Application logic can move exhausted jobs to a separate stream and define replay. | DLX routing can follow `requeue=false`, expiration, queue length overflow, or a quorum queue delivery limit. Default dead-letter forwarding lacks internal publisher confirms; quorum queues support at-least-once dead-lettering. Missing targets or outages can cause loss. | A separate dead-letter topic is a reasonable design pattern, but it was not established by substantive fetched Kafka documentation in this run. |
| Scalability | Consumer groups support worker pools; Redis Cluster shards keys across hash slots. Persistence, replication, failover, memory, and retention require planning. | Parallel consumers and prefetch support controlled concurrency. Capacity depends on queue type, persistence, workload, and downstream services; no benchmark is available. | **Provisional:** partitioned parallelism and its constraints (partition count, consumer assignment, key skew, and downstream capacity) are architectural observations in the findings, not verified by substantive Kafka documentation fetched in this run. |
| Operational complexity | Often attractive when Redis is already operated, but the application must own retry/DLQ policy, pending-entry recovery, idempotency, retention coordination, and cluster/failover planning. | Broker controls are explicit, but safe operation requires correct durability, DLX configuration, target availability, policies, and monitoring. | **Provisional:** the findings identify retention, lag, retry/DLQ topics, schema evolution, access control, and monitoring as operational concerns; this assessment is not supported by substantive Kafka documentation fetched in this run. |

### Interpretation for AI jobs

**Delivery and duplicate execution.** Acknowledgement should follow the point at which the job result or durable state transition is safely recorded. A worker crash after performing inference but before acknowledgement can lead to repeated work. Conversely, acknowledging before durable completion can lose work. Use a stable job ID, idempotent writes, and deduplication where repeated inference or side effects are costly. For long-running jobs, consider recording progress and lease/heartbeat state outside the broker message lifecycle.

**Ordering.** Define whether the requirement is enqueue order, per-entity order, or completion order. Parallel workers can complete jobs out of order even when the broker preserves an enqueue or partition order. If per-entity sequencing matters, route related jobs consistently and serialize processing for that key; global ordering generally limits parallelism.

**Retries and dead letters.** Separate transient failures (retry with bounded exponential backoff and jitter) from permanent failures (terminal dead-letter path). Preserve job ID, attempt count, error class, timestamps, and original payload/reference. Ensure replay is safe and that retry/DLQ backlogs are monitored. RabbitMQ provides the most directly documented dead-letter mechanisms in this evidence set, but its default forwarding safety is configuration-dependent. Redis and Kafka patterns require more application-owned policy based on the evidence available here.

**Scalability and operations.** Scale worker concurrency to actual GPU, model-serving, database, and external API capacity; broker throughput alone is not the objective. Redis may reduce platform overhead where Redis is already a managed dependency. RabbitMQ offers queue-specific controls but requires careful durability and DLX configuration. Kafka’s partitioned log and replay model may suit event-centric systems, but the evidence gap means teams should verify its current official semantics and operational requirements before committing.

### Source-page count and evidence quality

The findings preserve **five distinct source pages**: two Redis pages (`redis.io` Streams and Cluster scaling) and three RabbitMQ pages (confirms, DLX, and queues). The two Kafka links are fragment variants of one documentation page and count as one page, not two; the Kafka fetch did not provide substantive semantics content. Thus the five-page minimum is met by distinct Redis and RabbitMQ pages, but Kafka-specific conclusions remain lower confidence. All cited links below are exact URLs preserved in the findings. The Kafka ordering, partitioned scalability, and operational observations in the table are provisional architectural interpretations from the findings, not independently verified guarantees from substantive Kafka documentation.

## Recommendations

1. **For a conventional work queue with explicit acknowledgements and dead-letter routing, evaluate RabbitMQ first** when the team can configure durable queues, persistent messages, publisher confirms, bounded prefetch, and an appropriately safe DLX strategy. Test target-exchange outages and redelivery behavior.
2. **Choose Redis Streams when Redis is already a core dependency and stream/consumer-group behavior fits the workload.** Implement attempt tracking, backoff, dead-letter streams, idempotency, retention coordination, and recovery procedures explicitly; validate persistence and failover against the acceptable job-loss window.
3. **Choose Kafka when the system benefits from partitioned event logs, replay, and multiple independent consumers, and the organization can operate Kafka.** Before selection, verify current official Kafka documentation for producer/consumer guarantees, transactions, partition ordering, retention, and failure recovery; the evidence collected here is insufficient for a confident guarantee-level comparison.
4. **For all three, define the job contract before tuning the broker:** acknowledgement point, idempotency key, per-key ordering requirement, retry budget/backoff, terminal-failure handling, retention horizon, and maximum in-flight work. Run failure-injection tests for worker crash, broker/node restart, duplicate delivery, downstream outage, and DLQ target outage.

## Limitations

- The evidence is official product documentation, not a workload benchmark. No comparable throughput, latency, cost, or failure-rate measurements were collected; scalability and operational complexity are qualitative and workload-dependent.
- Kafka’s requested official documentation fetch returned a redirect shell without substantive semantics content. Its concepts fragment was not independently retrievable as a distinct page. Kafka-specific delivery, ordering, and operational claims are therefore provisional; no exact guarantee or default is asserted.
- Redis Streams evidence was reported as truncated. The findings support consumer-group and recovery concepts but do not establish a complete retry/DLQ feature comparison.
- RabbitMQ evidence is more detailed for queue controls, but does not constitute a complete deployment runbook. Dead-letter safety depends on queue type and configuration.
- Recommendations about idempotency, retry policy, concurrency, and job-state management are application design guidance, not guarantees supplied automatically by any broker.

## References

- [Redis Streams](https://redis.io/docs/latest/develop/data-types/streams/)
- [Scale with Redis Cluster](https://redis.io/docs/latest/operate/oss_and_stack/management/scaling/)
- [RabbitMQ: Consumer Acknowledgements and Publisher Confirms](https://www.rabbitmq.com/docs/confirms)
- [RabbitMQ: Dead Letter Exchanges](https://www.rabbitmq.com/docs/dlx)
- [RabbitMQ: Queues](https://www.rabbitmq.com/docs/queues)
- [Apache Kafka documentation — semantics](https://kafka.apache.org/documentation/#semantics)
- [Apache Kafka documentation — introduction, concepts and terms](https://kafka.apache.org/documentation/#intro_concepts_and_terms)
