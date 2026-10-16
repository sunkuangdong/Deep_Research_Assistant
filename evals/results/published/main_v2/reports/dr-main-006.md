## 背景

**摘要：** 推荐以持久化工作流状态为真相来源、以队列作异步分发、以业务副作用边界的幂等键处理重复，并将人工审批建模为可恢复状态机阶段；通过有界重试、事务协调和故障演练覆盖跨系统崩溃窗口。产品级审批 API 与 Kafka 交付语义在本轮证据中未核验。

企业 AI Agent 不只是一次请求/响应：它可能调用有副作用的外部工具、运行数分钟至数天、等待人工审批，并在进程重启、网络超时、队列重复投递或数据库冲突后继续执行。可靠性设计的核心不是假设“只执行一次”，而是让状态可恢复、重复动作可安全处理，并明确跨数据库、队列和外部工具的原子性边界。

本报告依据本轮检索并写入 findings 的六个不同页面，涵盖 LangGraph 持久化、Temporal 错误处理、Amazon SQS、AWS Builders' Library、PostgreSQL 事务隔离及 Apache Kafka 文档。六个页面是来源页面计数，不代表每页都支撑报告中的事实结论；Kafka 页面虽被保留，但其交付语义未核验，不据此作语义结论。

## 关键发现

1. **执行状态必须持久化，并与进程生命周期解耦。** LangGraph 文档区分单个 thread 的 checkpointer 与跨 thread 的 store；其 `InMemorySaver`/`MemorySaver` 在进程重启后会丢失检查点，生产环境应使用持久化后端并制定保留/清理策略。[LangGraph Persistence](https://docs.langchain.com/oss/python/langgraph/persistence)
2. **队列重复投递是正常故障条件。** Amazon SQS 标准队列可能重复交付，消费者必须幂等；队列消息不应成为业务状态的唯一真相来源。[Amazon SQS at-least-once delivery](https://docs.aws.amazon.com/AWSSimpleQueueService/latest/SQSDeveloperGuide/standard-queues-at-least-once-delivery.html)
3. **幂等性要覆盖业务副作用，而非只做消息去重。** 超时并不证明远端操作未发生；对有副作用的调用，重试前需有幂等令牌、持久化去重记录，或补偿/对账机制。[AWS Builders' Library：Timeouts, retries, and backoff with jitter](https://builder.aws.com/content/3EumjoZascWd1oZiEgL8ORlv3qE/timeouts-retries-and-backoff-with-jitter)
4. **人工审批应建模为持久化状态机阶段。** 审批请求、审批人/权限、输入版本、截止时间和结果应持久化；审批结果与恢复事件需可靠衔接，恢复时重新校验版本。具体产品 API 细节本轮证据不足，以上为架构建议而非产品事实。
5. **故障恢复需要有界重试与事务并发控制。** AWS 建议设置超时、重试上限、指数退避和抖动，避免多层重试放大故障；PostgreSQL 文档说明不同隔离级别提供不同快照/串行化保证，Repeatable Read 或 Serializable 下应用需准备处理序列化失败并重试事务。[PostgreSQL Transaction Isolation](https://www.postgresql.org/docs/current/transaction-iso.html)

## 证据与分析

### 推荐的状态与执行模型

将工作流实例、步骤、输入版本、审批状态、重试计数和恢复元数据保存在持久化状态库中；把执行检查点与跨任务长期业务记忆分层。LangGraph 文档支持 thread 检查点与跨 thread store 的区分；Temporal 错误处理指南说明 Workflow Task 可重试，修复并重新部署后可在不丢失 Workflow 状态的情况下继续。该 Temporal 结论仅限本轮取得的错误处理指南，不代表对其完整持久化架构的比较。[Temporal Error handling](https://docs.temporal.io/develop/python/best-practices/error-handling)

队列负责异步分发/唤醒，不负责充当业务真相。消费者收到消息后，应在持久化状态中校验任务是否仍可执行，并通过条件更新、唯一约束、锁或适当事务隔离处理并发竞争。PostgreSQL 文档指出 Read Committed 下连续查询可能看到不同快照；Repeatable Read 使用事务级快照，Serializable 提供串行化保证，而更强隔离级别下应用需准备处理序列化失败并重试事务。[PostgreSQL Transaction Isolation](https://www.postgresql.org/docs/current/transaction-iso.html)

### 幂等性与故障窗口

为每个有副作用的动作生成稳定幂等键，例如由工作流实例、步骤/动作标识和业务对象版本组成；在业务提交边界持久化动作状态/结果。若外部 API 支持幂等令牌，应将其传递给下游；否则需记录请求与响应、设计可重复安全操作，或提供补偿和对账流程。Temporal 文档也提示 Activity 可能重复执行，应设计为幂等操作。[Temporal Error handling](https://docs.temporal.io/develop/python/best-practices/error-handling)

重点处理以下崩溃窗口。以下 outbox/inbox、租约和审批状态机控制均为基于来源原则的工程推论，并非来源对特定 Agent 产品的直接承诺：

- 外部副作用已成功、工作流状态尚未提交：重试可能重复副作用；用外部幂等令牌、操作记录或补偿/对账控制。
- 业务状态已提交、消息尚未确认：消息可能重投；消费者应识别已完成动作并安全确认。
- 消息已确认、业务状态尚未提交：可能丢失工作；避免先确认后提交，采用事务性 outbox/inbox 或可恢复租约/扫描机制。
- 审批结果已保存、恢复事件未发出：审批结果与待恢复事件应通过同一事务/outbox 可靠衔接。
- 并发消费者争抢同一任务：使用原子认领、条件更新、唯一约束或锁，并处理事务冲突。

### 重试与恢复

为远程工具调用设置超时；明确单一重试责任层，设置最大次数/总预算、指数退避和随机抖动。对不可重试错误应进入失败/人工处置路径，而不是无限重试。对数据库序列化失败等可恢复冲突，按事务边界重试；对外部副作用不确定的超时，先查询/对账或使用幂等令牌，不能简单假定失败。

Kafka 官方页面在本轮未能核验交付语义，因此不对其 exactly-once 边界或与 SQS 的差异作结论。[Apache Kafka documentation](https://kafka.apache.org/0101/documentation.html)

### 适用场景与取舍

- 需要图式 Agent 状态检查点、线程连续性和长期记忆分层时，可评估 LangGraph 的 persistence 模型；生产可靠性取决于持久化后端和保留策略。
- 需要长时间运行任务在失败后继续时，可评估 Temporal 的 durable execution 能力；本轮证据仅覆盖错误处理指南，不能据此作全面产品排名。
- SQS 至少一次投递语义清晰，但要求消费者容忍重复；PostgreSQL 可提供事务和并发控制基础，但将队列与业务状态放在同一数据库可能带来容量、锁竞争和运维耦合。当前没有性能数据，无法量化这些取舍。

## 建议

1. **建立持久化工作流状态模型**：至少记录实例/步骤 ID、状态、输入版本、待执行动作、审批状态、重试预算、租约/心跳和恢复元数据；执行检查点与长期业务记忆分层。
2. **把队列当作分发层**：按至少一次投递设计；消息携带稳定工作流/步骤标识，消费者每次执行前都校验权威状态。
3. **在副作用边界实现幂等**：使用稳定动作幂等键、数据库唯一约束/去重记录；尽可能向外部工具传递幂等令牌。对不支持幂等的工具建立对账、补偿和人工处置流程。
4. **协调状态提交与消息发布/确认**：采用事务性 outbox/inbox 或等效机制，避免“状态已提交但事件丢失”及“消息已确认但状态未提交”。这是通用架构建议，需结合所选数据库和队列验证。
5. **将人工审批作为可恢复工作流阶段**：持久化审批请求、权限、版本、截止时间和结果；审批结果与恢复事件可靠衔接；恢复前重新校验当前状态和输入版本，重复审批请求应幂等。
6. **制定有界重试策略**：设置调用超时、最大次数/总预算、指数退避与抖动；明确重试责任层，区分可重试错误、永久错误和结果不确定的副作用超时。
7. **演练故障恢复**：测试进程重启、重复投递、数据库冲突、工具调用超时、审批后恢复事件丢失、过期租约和重试风暴；监控卡住任务、未投递 outbox、重复动作及审批超时。
8. **先验证再选型**：用真实工具副作用和故障注入验证恢复语义；补齐 Kafka 交付语义及各框架人工审批 API 的官方证据后，再做产品级比较。

## 局限性

- Temporal 证据来自错误处理指南，未覆盖完整持久化架构、事件历史、队列语义或人工审批 API。
- LangGraph 官方 interrupts 页面正文未成功取得；审批暂停/恢复的具体 API、输入回传和节点重放细节未核验。
- Kafka 页面为旧版文档入口，交付语义未核验，因此不作 exactly-once 或与 SQS 的语义比较。
- 没有吞吐量、延迟、成本、故障率、恢复时间目标或数据规模，无法量化性能、可用性、成本和保留策略。
- outbox/inbox、审批状态机、故障窗口控制及参考架构属于基于来源原则的工程推论。

### 参考资料

1. [LangGraph Persistence](https://docs.langchain.com/oss/python/langgraph/persistence)
2. [Temporal Python SDK Error handling](https://docs.temporal.io/develop/python/best-practices/error-handling)
3. [Amazon SQS at-least-once delivery](https://docs.aws.amazon.com/AWSSimpleQueueService/latest/SQSDeveloperGuide/standard-queues-at-least-once-delivery.html)
4. [Timeouts, retries, and backoff with jitter](https://builder.aws.com/content/3EumjoZascWd1oZiEgL8ORlv3qE/timeouts-retries-and-backoff-with-jitter)
5. [PostgreSQL Transaction Isolation](https://www.postgresql.org/docs/current/transaction-iso.html)
6. [Apache Kafka documentation](https://kafka.apache.org/0101/documentation.html)（页面已保留，但交付语义未核验）