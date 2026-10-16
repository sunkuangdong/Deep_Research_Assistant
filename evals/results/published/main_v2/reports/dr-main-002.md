# Temporal、Celery 与 AWS Step Functions：长时间运行 AI Agent 工作流适用性比较

## 背景

AI Agent 工作流可能跨越多次模型调用、外部工具执行、长时间等待和人工审批。此类流程的关键不只是把任务放入队列，还包括在进程或基础设施故障后恢复流程状态、控制重试与副作用、等待外部事件，并让团队能够运维和审计。Temporal、Celery 与 AWS Step Functions 的抽象层级不同：前者面向持久工作流执行，Celery 主要提供分布式任务执行，Step Functions 提供托管状态机编排。以下比较以官方文档为证据，并将产品事实与工程推论区分。

**执行摘要：** 长时间持久执行与人工审批是核心需求时，优先评估 Temporal 或 AWS Step Functions Standard；前者提供持久工作流与消息等待模型，后者提供 AWS 托管执行及明确的 Callback Task Token。Celery 更适合任务分发基础设施成熟、愿意自行补足流程状态与审批编排的团队。三者都不能替代对外部副作用的幂等、权限和审计设计。

## 关键发现

- **长时持久执行：** Temporal 官方概述称工作流执行历史会持久化，遇到崩溃、网络或基础设施中断后可恢复；AWS Step Functions Standard 在状态转换间持久化执行状态，最长运行一年，执行历史可通过 API 获取 90 天。[Temporal 官方概述](https://docs.temporal.io/)；[Step Functions 工作流类型](https://docs.aws.amazon.com/step-functions/latest/dg/choosing-workflow-type.html)。Celery 的任务确认与重投递可支持任务级恢复，但本次核验的官方页面没有证明 Celery 自身提供跨任务的完整持久工作流历史。[Celery Tasks](https://docs.celeryq.dev/en/stable/userguide/tasks.html)
- **人工审批：** Temporal 可通过 Signal 改变工作流状态并等待条件满足；AWS Step Functions Standard 的 Callback Task Token 模式明确支持暂停等待外部结果，官方列举人工审批场景。[Temporal 消息传递](https://docs.temporal.io/develop/python/workflows/message-passing)；[Step Functions Callback 模式](https://docs.aws.amazon.com/step-functions/latest/dg/connect-to-resource.html)。Celery 可由应用组合任务、队列和状态存储实现审批，但这不是本次证据所能确认的内建持久审批语义。
- **重试与副作用：** Celery 提供 `Task.retry()`，并强调任务幂等；其确认和重投递配置可能导致重复执行。[Celery Tasks](https://docs.celeryq.dev/en/stable/userguide/tasks.html)。Step Functions Standard 的工作流执行语义为 exactly-once，除非在 ASL 中配置 Retry；这不构成外部副作用端到端 exactly-once 的保证。Temporal 的具体重试策略页面本轮未成功核验，不能据此比较参数或默认值。
- **运维取舍：** Step Functions Standard 将执行状态和工作流运行时交由 AWS 托管，但仍需设计工作流、权限、错误策略和外部副作用幂等。Temporal 可自托管或使用 Temporal Cloud；自托管运维成本本轮未量化。Celery 灵活；broker、worker、确认语义、超时和路由等部署责任是基于其任务执行模型的运维判断，具体组件与监控安排取决于部署方式。

## 证据与分析

### 状态持久化与故障恢复

Temporal 的官方平台概述将持久化执行历史与故障后恢复作为核心能力，适合需要跨进程生命周期保存流程进度的 Agent。其 Python SDK 消息传递文档还说明 Signal 等消息会进入工作流历史。实际恢复仍依赖工作流实现遵循 SDK 约束，不能把平台能力等同于任意代码都可无条件恢复。[Temporal 官方概述](https://docs.temporal.io/)；[Workflow message passing - Python SDK](https://docs.temporal.io/develop/python/workflows/message-passing)

Step Functions Standard 的官方工作流类型说明给出明确边界：最长运行一年，状态在状态转换间持久化，执行历史可通过 API 获取 90 天。Express 最长五分钟且不在状态转换间持久化，因此不适合需要长时间等待和持久状态的流程。[Choosing workflow type in Step Functions](https://docs.aws.amazon.com/step-functions/latest/dg/choosing-workflow-type.html)。Celery 官方 Tasks 文档描述的是任务消息确认、worker 丢失和重投递行为；恢复结果受 broker、确认时机和配置影响，不能直接等同于完整工作流状态恢复。[Celery Tasks](https://docs.celeryq.dev/en/stable/userguide/tasks.html)。对有副作用的 Agent 工具调用，Celery 场景尤其需要幂等键、去重或补偿设计。

### 重试

Celery 的 `Task.retry()` 提供任务级重试入口，但重试与消息确认、worker 故障和重复执行语义需要一起设计。官方文档强调任务应尽量幂等。[Celery Tasks](https://docs.celeryq.dev/en/stable/userguide/tasks.html)。Step Functions Standard 的工作流执行语义为 exactly-once，除非在状态机定义中配置 Retry；这描述的是工作流执行语义，不保证外部副作用端到端 exactly-once，外部调用仍需考虑幂等或去重。[Choosing workflow type in Step Functions](https://docs.aws.amazon.com/step-functions/latest/dg/choosing-workflow-type.html)。Temporal 本轮未取得官方重试策略页面的可核验内容，无法比较其重试配置粒度、默认值或 Activity 与 Workflow 的差异。不能据此推断 Temporal 缺少重试能力，只能说本次证据不足。

### 人工审批与外部等待

Temporal 的 Signal 可异步改变工作流状态，工作流可等待条件满足后继续；Update 可用于需要同步确认接受或拒绝的交互，但调用方等待的是 Worker 对 Update 的接受/拒绝，不应等同于审批业务结果已完成。Signal 被服务端接受也不代表工作流已处理。[Workflow message passing - Python SDK](https://docs.temporal.io/develop/python/workflows/message-passing)。AWS Step Functions Callback Task Token 提供明确的暂停/恢复接口：外部系统将原 token 与结果通过 `SendTaskSuccess` 或 `SendTaskFailure` 返回后，工作流继续。官方文档将人工审批列为适用场景，并说明该模式仅适用于 Standard Workflows，涉及 IAM 权限、同账户 token 传递及超时约束。[Discover service integration patterns in Step Functions](https://docs.aws.amazon.com/step-functions/latest/dg/connect-to-resource.html)。两者都不替代审批人身份验证、授权、审计和升级策略。

### 运维复杂度与适用场景

| 方案 | 更适合的场景 | 主要优势 | 主要代价或风险 |
|---|---|---|---|
| Temporal | 需要长时间持久运行、跨故障恢复、等待外部事件/审批，且希望以代码表达复杂流程的 Agent 系统 | 持久工作流历史；Signal/Update 等交互模型；可自托管或使用 Temporal Cloud | 自托管的数据库、升级、备份、容量和可观测性负担本轮未量化；需遵循工作流实现约束；重试细节证据缺口 |
| Celery | 以异步任务分发、后台执行和任务级重试为主，团队愿意自行组合流程状态与编排的系统 | 任务执行灵活；可配置重试、确认和 worker 路由 | 任务级语义不等于完整持久工作流；broker/worker 与状态管理责任较多；重复执行、阻塞和幂等风险需应用处理。组件与监控责任属于部署相关的工程判断 |
| AWS Step Functions Standard | 已在 AWS 环境、希望采用托管工作流执行，并需要长时等待或人工审批回调的系统 | 托管状态持久化与执行历史；Callback Task Token 明确支持外部/人工回调 | AWS/IAM 与服务集成约束；仍需设计错误策略、业务状态和外部副作用幂等；Express 不适合长时 Callback 流程 |

总体而言，若“长时间运行 + 人工审批 + 故障恢复”是核心要求，Temporal 与 Step Functions Standard 是更直接匹配的候选。Temporal 更适合希望以代码构建持久工作流、并需要部署选择的团队；Step Functions Standard 更适合 AWS 原生、偏好托管编排且接受 AWS 集成边界的团队。Celery 并非不能实现此类系统，但应将额外的状态管理、审批恢复和运维工作纳入总成本，而不应仅凭任务重试能力视为完整工作流引擎。

## 建议

1. **优先评估 Temporal**：当 Agent 流程复杂、需要长时间等待、跨故障恢复和多种外部消息交互，且团队能承担自托管运维或采用 Temporal Cloud 时。
2. **优先评估 AWS Step Functions Standard**：当系统主要运行在 AWS、希望减少工作流运行时自运维，并需要明确的人工审批回调模式时。不要将 Express 用于长时间等待或 Callback 审批。
3. **选择 Celery 的前提**：流程主要是可拆分的后台任务，团队已有成熟 broker/worker 运维能力，并愿意自行实现持久业务状态、审批等待、恢复编排、幂等和审计。
4. **无论选择何者**：对模型调用和工具副作用定义幂等策略；明确重试边界、超时、人工审批授权与审计；通过故障注入验证恢复行为，而不是仅依赖产品级语义描述。

## 局限性

本次 Temporal 重试策略与自托管运维细节未取得可核验的官方页面；Celery 证据未覆盖结果后端持久化保证或完整工作流历史；Step Functions 的 Retry/Catch 细节未核实。运维复杂度比较因此是定性判断，Celery 组件责任部分属于基于任务语义的工程推论。官方文档描述的是平台能力，不构成特定 Agent 应用的端到端可靠性保证；实际结果还取决于 SDK/工作流实现、外部服务、权限、幂等和部署配置。

## 参考资料

1. [Temporal Platform Documentation](https://docs.temporal.io/)
2. [Workflow message passing - Python SDK](https://docs.temporal.io/develop/python/workflows/message-passing)
3. [Celery Tasks](https://docs.celeryq.dev/en/stable/userguide/tasks.html)
4. [Choosing workflow type in Step Functions](https://docs.aws.amazon.com/step-functions/latest/dg/choosing-workflow-type.html)
5. [Discover service integration patterns in Step Functions](https://docs.aws.amazon.com/step-functions/latest/dg/connect-to-resource.html)
