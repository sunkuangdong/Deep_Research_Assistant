# Kubernetes 上部署有状态 Agent 工作流：实践报告

## 背景

有状态 Agent 工作流会跨多个步骤调用模型、工具和外部服务，执行时间可能长于单个 Pod 生命周期。生产部署需要同时解决任务如何可靠分发、执行进度如何持久化、工作者如何随积压扩缩，以及 Pod 被缩容或重启时如何安全交接。Kubernetes 提供工作负载控制器和扩缩容机制，但队列确认、Agent 检查点和外部副作用的一致性仍需由应用与存储协议共同设计。

## 关键发现

1. **把队列、工作负载控制器和执行状态分层。** 持续消费任务通常适合“持久队列 + Deployment 工作池”；有限且有明确完成条件的任务可用 Job。Job 不是消息队列，Deployment/StatefulSet 也不提供消息确认、租约或 exactly-once 执行。
2. **检查点必须落在进程外的持久化后端。** LangGraph 文档区分单个 thread 的 checkpointer 与跨 thread 的长期 store；内存型 saver 在进程重启后丢失状态。生产恢复应使用持久化 checkpointer，并将外部副作用的幂等/补偿单独设计。
3. **扩缩容不等于任务交接。** KEDA 可基于事件源指标驱动长期工作负载扩缩；副本数、单副本并发和队列分配机制是不同控制层。缩容时仍需消费者停止领取、完成或释放在途任务。
4. **重试与恢复必须按可能重复执行来防御。** 队列重投递、Job 重试或结果提交后确认失败都可能造成重复执行。应先持久化结果/检查点再确认消息，并对工具调用、写库等副作用使用幂等键、事务或补偿逻辑。
5. **StatefulSet 不是 Agent 状态管理方案。** 它适用于需要稳定身份或持久存储的服务（例如自托管数据库）；Agent 执行状态应由应用检查点协议管理。

## 证据与分析

### 任务队列与工作负载选择

Kubernetes Job 面向有完成目标的有限任务，可控制并行度、完成数并配置失败重试；它不提供消息级确认。KEDA ScaledObject 可驱动 Deployment、StatefulSet 等长期运行工作负载按事件源扩缩，工作者从事件源拉取任务；KEDA 文档指出事件源可保留自身的重试、死信和 checkpoint 等处理语义。由此，持续到达的队列任务通常由持久队列承担分发与确认语义、Deployment 管理工作者副本；有限批处理或独立任务可考虑 Job。若由队列触发创建 Job，仍需额外协调领取、重复派发、完成跟踪和清理。后几项属于架构推论，具体行为取决于队列与应用实现。

### 检查点与持久化

LangGraph 官方文档将 checkpointer 定位为单个 thread 的图状态检查点，将 store 定位为跨 thread 的长期应用数据。内存型 saver 不适用于进程重启后的恢复；生产环境应考虑 PostgreSQL 等持久化 checkpointer。StatefulSet 可管理自托管数据库的稳定身份和存储关联，但不是检查点协议本身。检查点恢复也不意味着任意外部 API 调用或数据库事务会自动回滚或 exactly-once 重放。

### 横向扩缩容

KEDA 监测事件源并向 HPA 提供指标，可按事件负载调整工作者副本；其文档说明空闲时可缩至零。扩缩容只改变工作者容量，不负责任务租约、确认或安全交接。实践中应分别设置副本规模、每副本并发/批量和队列分配策略；长时间 Agent 步骤还需考虑下游限流，避免扩容放大外部调用压力。具体队列指标接入、扩缩容响应和缩容行为依赖所选 scaler、队列及配置。

### 优雅终止与重试

建议工作者退出时先停止领取新任务，再完成在途任务并持久化检查点；无法完成时安全释放任务或让租约到期重投递。只有在结果或必要状态可靠持久化后才确认消息。确认早于持久化可能丢任务；持久化成功但确认失败则可能重复执行。Job 重试和队列重投递都不能替代应用幂等性。上述退出顺序是工程建议，不是本次已核验的 Kubernetes 终止流程；本次 findings 未记录足以支持具体终止信号时序、宽限期或钩子配置的条款，因此不对这些参数作确定性断言。

### 综合取舍

默认架构建议为“持久队列 + Deployment 工作池 + 外部持久化 checkpointer”，适合持续到达、需要弹性消费的 Agent 工作流。Job 更适合有限、可独立完成的任务；StatefulSet 仅在工作者或其依赖确有稳定身份/持久卷需求时采用。端到端可靠性来自队列协议、检查点持久化、幂等副作用和退出交接的组合，而不是单一 Kubernetes 控制器。

## 建议

- 以持久队列作为任务事实来源，明确消息确认、租约/可见性超时、重投递、死信和去重语义；不要把 Kubernetes Job 或副本控制器当作队列。具体协议需按所选队列验证。
- 将 Agent thread 检查点写入进程外的持久化存储；区分短期执行检查点与跨 thread 长期记忆，并制定备份、保留和清理策略。
- 采用 Deployment 管理常驻消费者，按队列指标配置 KEDA/HPA；分别限制副本数、每副本并发和下游调用速率。对有限任务再评估 Job。
- 将“停止领取、处理或释放在途任务、持久化进度、最后确认”作为应用层优雅退出协议；终止宽限期与最长任务阶段时长的匹配属于实施设计，需结合 Kubernetes 版本和应用行为验证，并通过故障注入测试。
- 对所有可重试的外部副作用使用幂等键、事务或补偿；测试 Pod 被杀、节点中断、队列租约过期、检查点写入失败和确认失败等场景。
- 在真实负载下测量任务时长、积压、吞吐、恢复时间、存储延迟和下游限流，再确定扩缩容阈值与容量参数；现有证据不足以给出通用数值。

## 局限性

本次证据以 Kubernetes、KEDA 和 LangGraph 官方文档为主。findings 对 Pod lifecycle 与 HPA 页面未记录足够具体条款，因此报告不推断终止信号时序、HPA 算法参数或队列指标接入细节。队列产品、Agent 框架、数据库实现和集群版本未指定，确认/租约、重试退避、检查点原子性、高可用与备份策略均需按具体实现验证。没有吞吐、延迟、任务时长、成本或失败率数据，无法量化比较架构性能或给出副本数、并发度和阈值。官方文档描述的是组件能力，不构成端到端 exactly-once、无损终止或外部副作用自动恢复保证。

## 参考资料

### 官方来源
- [Jobs | Kubernetes](https://kubernetes.io/docs/concepts/workloads/controllers/job/)
- [Scaling Deployments, StatefulSets & Custom Resources | KEDA](https://keda.sh/docs/2.21/concepts/scaling-deployments/)
- [Persistence - Docs by LangChain](https://docs.langchain.com/oss/python/langgraph/persistence)
- [StatefulSets | Kubernetes](https://kubernetes.io/docs/concepts/workloads/controllers/statefulset/)

### 第三方来源
- [k8s hpa简介 - SegmentFault 思否](https://segmentfault.com/a/1190000022790270?utm_source=sf-similar-article)（仅作为有限背景材料，不作为关键结论依据）