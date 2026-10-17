# 企业 AI Agent 平台可靠性架构：状态、队列、幂等与恢复

## 背景

企业 AI Agent 不只是一次请求/响应：它可能跨越多个工具调用、等待外部系统、暂停数小时或数天等待人工审批，并在进程、网络、队列或工具故障后继续执行。可靠性设计的核心不是追求一个笼统的“恰好一次”，而是明确每个持久化边界、恢复权威和副作用边界。

本报告综合 LangGraph 与 Temporal 官方工作流文档、AWS 幂等 API 与 Transactional Outbox 指南，以及 Apache Kafka 文档页面。证据支持的机制与基于机制推导的架构建议分别说明；具体产品保证仍需按部署配置核实。

## 关键发现

1. **工作流状态必须持久化，且恢复模型要明确。** LangGraph 的 checkpointer 保存单个 thread 的图状态，Store 用于跨 thread 的应用数据；内存 saver 在进程重启后丢失状态，生产环境应使用持久化后端并管理 checkpoint 保留与清理。[LangGraph Persistence](https://docs.langchain.com/oss/python/langgraph/persistence)
2. **检查点与事件历史重放不是同一种恢复语义。** Temporal 记录 Workflow 的 Commands/Events，并通过确定性重放重建状态；Activity 结果可在重放时复用。Workflow 代码必须满足重放确定性，外部交互应放在 Activity 边界。[Temporal Workflows](https://docs.temporal.io/workflows)
3. **至少一次投递下，重复消息是预期情况。** Transactional Outbox 可将业务状态变更与待发布事件放在同一数据库事务，但 relay 崩溃仍可能造成重复发布，消费者仍需幂等处理。[AWS Transactional Outbox](https://docs.aws.amazon.com/prescriptive-guidance/latest/cloud-design-patterns/transactional-outbox.html)
4. **幂等键应代表同一业务意图，并贯穿重试与人工重放。** AWS 的幂等 API 指南强调由调用方提供稳定请求标识，服务端持久化标识及结果，使重复请求返回既有结果而不重复产生副作用。[AWS Making retries safe with idempotent APIs](https://aws.amazon.com/builders-library/making-retries-safe-with-idempotent-APIs/)
5. **队列事务不能自动覆盖外部工具副作用（架构推断）。** 工具成功但响应丢失时，平台可能无法判断操作是否已发生。应使用外部幂等键、操作状态查询、持久化操作账本或人工核查；不可逆操作不能假设可回滚。Kafka 页面在本轮抓取中未呈现语义正文，因此不据此作产品级保证判断。[Kafka 文档页面](https://kafka.apache.org/documentation/#semantics)
6. **人工审批应是持久化状态转换，而非占用进程等待（架构建议）。** 将任务置为待审批、保存必要上下文并释放执行资源；审批通过/拒绝作为可审计事件触发恢复。具体框架 API、超时、取消和权限语义在本轮官方证据中未充分核实。

## 证据与分析

### 状态存储与恢复

建议将任务业务状态、工作流引擎状态、消息投递状态、工具操作状态和审批记录分层持久化，并通过稳定标识关联。工作流状态应有唯一权威来源：可以是持久化 checkpoint，也可以是事件历史重放；避免多个服务同时写入互相冲突的“任务当前状态”。这是基于来源机制的架构建议，不是某一框架的产品保证。

Checkpoint 型机制便于保存并检查当前图状态，适合需要按线程恢复、检查或人工介入的流程；代价是需管理后端可用性、状态版本兼容、保留与清理。事件历史重放适合长时间运行且需要从已记录历史恢复的编排，但要求 Workflow 决策可重放，外部调用必须隔离在可记录结果的活动边界。两者是不同的恢复模型，不应把“有 checkpoint”误认为外部副作用已去重。

### 队列、幂等与副作用

推荐采用“数据库事务写业务状态与 outbox → relay 发布消息 → 消费者幂等执行”的链路。Outbox 缩小数据库提交与消息发布之间的双写不一致窗口，但不消除重复投递。消费者应以稳定的 `task_id`、`step_id`、`operation_id` 建立持久化操作账本；同一业务意图的重试、死信重放和人工重放沿用同一幂等键。这些是基于 AWS 幂等与 Outbox 机制推导的架构建议。

工具调用应显式记录“待执行、执行中、成功、失败、结果未知”等状态。遇到超时等结果未知情形，优先用同一幂等键重试或查询外部操作状态；若工具不支持幂等键或查询，则进入对账/人工核查路径，避免盲目重复执行。队列确认、工作流状态提交和外部工具成功是不同边界，不能合并成一个“完成”标志。Kafka 页面本轮未呈现语义正文，故本段不将其作为 Kafka 特定保证。

### 人工审批与故障恢复

审批等待应持久化为任务状态，例如 `WAITING_APPROVAL`，并记录任务版本、审批主体、决策、时间及关联操作 ID。审批事件需校验权限、版本和重复提交；通过后恢复原工作流，拒绝、撤回、超时和取消应有明确终态。此为架构建议；本轮资料未核实具体框架 API 与安全语义。

对暂时性错误采用有上限的指数退避与抖动；永久错误停止自动重试；结果未知先查询或以原幂等键重试。超过策略后进入死信队列，保留原始标识、错误分类、尝试记录和上下文。死信是隔离与恢复入口，不是任务完成状态。跨服务长流程可为可逆步骤定义幂等补偿；补偿失败应可重试并升级人工处理，不可逆副作用则需后续纠正而非假称回滚。这些属于通用可靠性设计建议，具体队列行为需按产品文档验证。

### 参考架构

1. API 接收请求并确定稳定 `task_id`；事务写入任务记录、初始状态和 outbox 事件。
2. Outbox relay 发布事件并记录发布进度；允许重复发布，监控积压与最老记录年龄。
3. 工作流引擎使用一种明确的恢复权威：持久化 checkpoint 或确定性事件历史重放。
4. 消费者通过持久化幂等账本检查 `task_id + step_id + operation_id`；调用工具时传递同一幂等键，记录结果或未知状态。
5. 审批点持久化待审批状态并释放执行资源；审批事件经授权与版本校验后唤醒原任务。
6. 有界重试、死信、同键重放、补偿和人工升级形成闭环；统一关联任务、消息、工具操作与审批审计。

## 建议

- **先定义状态机和提交边界。** 明确任务、步骤、工具操作、审批、消息各自的状态及合法转换；区分“已排队”“已执行”“结果未知”“待审批”和“已完成”。
- **采用持久化状态 + Outbox + 至少一次队列 + 幂等操作账本。** 这是基于本轮来源所述持久化、重复投递和幂等机制的组合建议，不代表未指定队列产品的投递保证。
- **为每个业务意图生成稳定幂等标识。** 从入口贯穿步骤、工具调用、审批恢复、死信重放和补偿；不要在重试时生成新键。
- **把人工审批设计成可恢复的持久化等待。** 保存最小必要上下文，释放 worker；审批记录不可变、可审计，并校验权限、任务版本、重复事件和过期决策。
- **按工作流特征选择恢复模型。** 若重视可检查的当前状态，可评估 checkpoint；若需要长时间运行的历史重放且团队能保证确定性，可评估事件历史模型。不要在缺少负载、成本和恢复目标数据时宣称某一种普遍更优。
- **演练故障边界。** 至少测试：提交后进程崩溃、重复投递、工具成功但响应丢失、审批重复/过期/拒绝、死信重放、补偿失败及代码升级后的恢复兼容性。监控 outbox/死信积压、最老消息年龄、重试次数、审批等待时长和结果未知操作数。

## 局限性

本轮资料未提供具体业务负载、任务时长分布、吞吐量、可用性目标、RPO/RTO、成本或延迟数据，因此无法量化比较 checkpoint 与事件历史的性能、存储成本或恢复时间。人工审批的具体 API、超时/取消语义、权限模型和数据安全边界未充分核实；队列产品也未指定，投递保证、事务、去重窗口、顺序性和死信行为需按实际产品验证。外部工具是否支持幂等键、操作查询、撤销或补偿未知。Kafka 页面本轮未呈现语义正文，相关证据有限；因此本报告不把该页面计作有实质内容支撑的来源。

## 参考资料

以下列出本轮核验的五个不同页面。前四个页面提供了本报告所用的实质性机制依据；Kafka 页面虽为本轮返回的不同页面，但本轮抓取未呈现语义正文，仅作为待进一步核实的官方文档入口，不作为关键结论的实质证据。

1. [LangGraph Persistence](https://docs.langchain.com/oss/python/langgraph/persistence)
2. [Temporal Workflows](https://docs.temporal.io/workflows)
3. [AWS Builders’ Library: Making retries safe with idempotent APIs](https://aws.amazon.com/builders-library/making-retries-safe-with-idempotent-APIs/)
4. [AWS Prescriptive Guidance: Transactional outbox pattern](https://docs.aws.amazon.com/prescriptive-guidance/latest/cloud-design-patterns/transactional-outbox.html)
5. [Apache Kafka Documentation](https://kafka.apache.org/documentation/#semantics)
