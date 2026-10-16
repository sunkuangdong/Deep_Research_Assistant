## 背景

长时间运行的 AI Agent 工作流可能跨越多次模型调用、工具执行、外部系统等待与人工审批；执行过程还可能遭遇进程重启、网络中断、服务限流或重复投递。编排方案的关键差异，在于谁负责保存流程状态、如何从故障中恢复，以及人工等待和运维责任落在哪里。

本报告比较 Temporal、Celery 与 AWS Step Functions，聚焦状态持久化、重试、人工审批、故障恢复和运维复杂度。证据以本轮核验的三家官方文档为主；适用性判断属于基于产品机制的工程分析，不是同环境基准测试。

## 关键发现

1. **长流程状态模型不同。** Temporal 以 Workflow Event History 为状态事实来源，故障后通过重放重建工作流状态；Step Functions Standard 在状态转换间持久化执行状态，最长运行一年；Celery 的任务状态/结果机制不等于完整的 Agent 业务流程状态，长流程进度通常需要应用层另行持久化。
2. **重试与恢复都不能替代幂等设计。** Celery 明确提供任务级重试，但消息重投和 worker 故障语义受 broker、确认时机及配置影响。Step Functions Standard 只有显式配置 Retry 才会重试状态；Temporal 的本轮证据支持事件历史重放，但未核实具体重试参数。三者都不能自动回滚已发生的外部副作用。
3. **人工审批的原生支持证据以 Step Functions 最明确。** Standard Workflow 的 Callback（`.waitForTaskToken`）可暂停并等待外部主体回传令牌，官方文档列出人工审批场景。Celery 更适合由应用保存等待状态、审批后再派发续跑任务；Temporal 的人工等待机制本轮未充分核实，不能据此断言其能力缺失或具体实现细节。
4. **运维责任只是转移而非消失。** Temporal 需要遵守确定性重放并治理 Activities 与平台运行；Celery 需要管理 broker、worker、确认/重连、队列与任务状态；Step Functions 托管状态推进，但仍需管理 IAM、令牌、超时/心跳、日志告警、配额、历史保留和状态转换成本。
5. **没有足够同口径数据给出绝对排名。** 本轮资料未提供吞吐、延迟、成本、可用性或运维工时的可比实测数据，选择应由流程形态、现有基础设施和团队能力驱动。

## 证据与分析

### 横向比较

| 维度 | Temporal | Celery | AWS Step Functions |
|---|---|---|---|
| 状态持久化 | 官方文档描述事件历史记录工作流事件，恢复时重放历史重建状态；外部交互由 Activities 承担。 | 任务状态/结果依赖配置与 backend；业务级长流程状态、审批记录和幂等键宜由应用持久化。 | Standard 在状态转换间持久化状态，最长一年；执行完成后历史可查询 90 天。Express 最长五分钟且不在状态转换间持久化。 |
| 重试 | 本轮已核实重放与 Activity 边界，但未核实具体重试策略参数；外部副作用需单独治理。 | `self.retry()` 等任务级机制可用于重试；任务应尽量幂等，重投语义受确认设置和 broker 影响。 | Standard 默认 exactly-once；需显式配置 Retry 才会再次运行状态。Express 的执行语义不同。 |
| 人工审批 | 本轮来源未覆盖具体人工等待机制，结论不确定。 | 未发现专门内建审批原语；可由应用记录等待状态，审批后重新派发，避免 worker 阻塞。 | Standard Callback 可通过 task token 等待外部回传，官方明确列出人工审批用途；需处理令牌、超时/心跳及账户约束。 |
| 故障恢复 | 事件历史可用于重建工作流状态；不意味着外部副作用自动回滚。 | worker 故障后的重投取决于 ack、broker 和配置；需在目标环境验证重复执行与丢失风险。 | 持久状态和执行历史有助于定位失败步骤；仍需设计 Retry/Catch、补偿或人工介入，外部副作用不自动回滚。 |
| 运维复杂度 | 需遵守重放安全约束，管理工作流/Activity 与平台；本轮未核实生产运维成本。 | 需管理 broker、worker、队列、并发、停机、重连、监控和应用层流程状态。 | 服务托管状态推进，但需管理状态机、IAM、令牌、超时、日志、配额、历史保留和计费。 |

### 取舍与适用场景

- **Temporal：** 可优先评估于需要跨长时间等待、在应用或基础设施故障后从持久历史继续执行，且团队愿意采用 Workflow/Activity 模型并保证重放安全的 Agent 流程。优势是工作流状态恢复模型清晰；代价是代码需满足重放约束，外部副作用仍需幂等与超时治理，平台运维细节需结合部署方式评估。
- **Celery：** 可优先评估于已有 Celery、broker 与 worker 体系，流程可拆成异步任务，且团队愿意在应用数据库或事件系统中维护业务进度和审批状态的场景。优势是可复用现有任务基础设施；代价是长流程状态机、人工等待和跨步骤恢复更多由应用组合，故障语义依赖配置与 broker。
- **AWS Step Functions Standard：** 可优先评估于 AWS 服务集成较多、需要托管状态推进、执行历史和明确人工审批等待的流程。优势是托管编排与 Callback 模式；代价是 AWS 权限、配额、令牌安全、状态转换计费及服务边界。Express 不适合作为长时间运行主流程的直接承载类型。

### 证据边界与参考资料

本轮 findings 记录了 6 个不同且成功验证的官方文档页面：Temporal 2 页、Celery 2 页、AWS Step Functions 2 页。Temporal 另有一次抓取失败，不计入来源数量。分析没有新增来源。官方文档支持产品机制描述；复杂度、架构适配和建议属于定性工程推断，而非同环境实测或普遍适用的排名。

- Temporal Platform Documentation: https://docs.temporal.io/
- Temporal Workflow: https://docs.temporal.io/workflows
- Celery Tasks — Celery 5.6.3 documentation: https://docs.celeryq.dev/en/stable/userguide/tasks.html
- Celery Workers Guide — Celery 5.6.3 documentation: https://docs.celeryq.dev/en/stable/userguide/workers.html
- Choosing workflow type in Step Functions: https://docs.aws.amazon.com/step-functions/latest/dg/choosing-workflow-type.html
- Discover service integration patterns in Step Functions: https://docs.aws.amazon.com/step-functions/latest/dg/connect-to-resource.html

## 建议

1. **先按流程状态与等待模式筛选。** 若需要长时间持久执行和故障后续跑，优先评估 Temporal；若人工审批是核心且流程主要在 AWS 内，优先评估 Step Functions Standard；若已有 Celery 体系且可接受应用层维护流程状态，Celery 可作为低迁移成本选项。
2. **把业务状态与执行状态分开设计。** 无论采用哪种方案，都应持久化 Agent 阶段结果、审批记录、外部调用幂等键和可恢复检查点；不要把队列消息或进程内存当作唯一业务记录。
3. **对外部副作用做幂等与补偿。** LLM/工具调用、支付、写入或发送操作应有幂等键、超时、重试上限和必要的补偿/人工处置路径。编排器的状态持久化不等于外部事务回滚。
4. **用故障注入验证真实语义。** 在目标 broker、云区域和配置下测试 worker/进程终止、网络断连、重复回调、审批超时、外部 API 超时及重启恢复；同时测量成本、恢复时间、队列积压和人工运维负担。
5. **将人工审批设计为持久等待而非占用执行资源。** 对 Celery 尤其避免 worker 长时间阻塞；对 Step Functions Callback 管理令牌安全、超时和回调权限；对 Temporal 则在选型验证中专门确认所需的等待/信号模式与运维实现。

## 局限性

- Temporal 本轮已验证页面主要覆盖平台概览与 Workflows；重试策略参数、人工审批具体机制及生产告警、容量、升级运维细节未充分核实。因此不能把“未检索到具体证据”解释为产品不支持。
- Celery 的结果 backend 具体配置、过期策略及不同 broker 下的故障语义未做完整验证；人工审批建议是应用层架构模式，不是已证实的内建审批功能。
- Step Functions 的 ASL Retry/Catch 字段细节、区域配额数值、成本估算及 Agent 专属最佳实践未核实；服务持久化不代表外部副作用具备事务性回滚。
- 三者没有同一环境下的性能、成本、可用性或运维工时数据，不能据此给出绝对优胜者。实际结果会受版本、部署方式、broker、云区域、工作流设计和团队经验影响。
