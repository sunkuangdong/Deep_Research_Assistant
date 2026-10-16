# 多 Agent 深度调研系统的上下文与调用治理

## 背景

多 Agent 深度调研通过并行委派扩大探索能力，但也可能让主 Agent 的上下文被子任务轨迹、重复摘要和工具结果挤占；同时，若交接和停止条件不明确，工作流可能出现状态丢失、重复调用或持续运行。官方框架文档与工程文章显示，治理并非单一的“缩短上下文”问题，而是要分别管理探索过程、跨步骤状态和执行边界。

## 关键发现

1. **上下文隔离把探索过程与主流程分开，但不等于降低总成本。** LangChain Deep Agents 概览将隔离上下文中的子代理、摘要和长结果卸载列为能力；Anthropic 的 orchestrator-workers 设计则让子代理独立探索，再把重要发现压缩回传。这样可减少主 Agent 直接承载全部探索细节，但并行代理会增加总 token 消耗，摘要也可能损失细节。[Deep Agents overview](https://docs.langchain.com/oss/python/deepagents/overview)；[Anthropic multi-agent research system](https://www.anthropic.com/engineering/multi-agent-research-system)
2. **控制权交接与状态持久化应传递最小必要信息，并区分短期状态与长期数据。** OpenAI Agents SDK 的 handoff 可转移控制权并配置输入、回调和历史过滤；LangGraph 将线程内检查点与跨线程 Store 区分，支持恢复与状态复用。交接字段需校验，持久化状态需有保留和清理策略。本报告未核实 Deep Agents filesystem 的文件交接实现，因此不将其作为已证实能力。[OpenAI Agents SDK: Handoffs](https://openai.github.io/openai-agents-python/handoffs/)；[LangGraph: Persistence](https://docs.langchain.com/oss/python/langgraph/persistence)
3. **终止条件与预算边界是防止无界调用的执行控制面，但证据支持范围不同。** AutoGen Teams 文档展示了基于文本条件停止团队及查看停止原因的模式；本轮证据未核实其 `max_turns` 的精确语义，也未证明该页面提供调用、时间或 token 硬预算能力。后者是本报告建议在应用层自行设置的治理措施，应与框架文档已证实的终止条件区分。[AutoGen: Teams](https://microsoft.github.io/autogen/stable/user-guide/agentchat-user-guide/tutorial/teams.html)
4. **三类机制互补：隔离管过程，控制权交接与持久化管状态，预算/终止管边界。** 只做隔离可能增加总调用成本；只做状态持久化可能造成状态膨胀；只设停止条件则不能避免主上下文被冗长轨迹占满。组合治理更完整。

## 证据与分析

| 机制 | 控制对象 | 抑制失控的路径 | 主要权衡与适用场景 |
|---|---|---|---|
| 子 Agent 上下文隔离 | 探索过程与上下文窗口 | 子任务在独立窗口运行，主 Agent 接收压缩后的结果 | 适合边界清晰、可并行且可摘要的任务；多 Agent 增加 token 成本，压缩可能遗漏信息；强耦合任务不宜强行拆分。 |
| 控制权交接与状态持久化 | 跨步骤传递和恢复的状态 | 只传必要摘要/结构化字段，或从检查点恢复，而非反复携带完整历史 | 适合长任务、多阶段流程和故障恢复；需校验交接字段、控制历史可见范围，并治理持久化增长。 |
| 预算与终止控制 | 调用次数、运行时长及停止条件 | 通过明确停止信号和应用层硬边界限制循环与重复调用 | 适合有审批节点、完成信号或资源上限的工作流；条件过早会截断任务，过宽或缺失则可能无法及时停止。框架来源已核实的是 AutoGen 文本终止条件示例；调用、时间或 token 硬预算属于应用层建议，非该来源已证实能力。 |

建议将三者组成闭环：先把可并行任务放入隔离上下文；子 Agent 以结构化格式返回结论、依据、未解决问题和完成状态；主 Agent 校验交接内容与权限后再继续；每次调用前后检查预算、停止原因和持久化状态规模。关键计划应外置保存，避免仅依赖可能被截断的对话历史。生产环境还应记录调用、交接、摘要和终止原因，以便审计压缩损失和重复执行。

本次没有可跨框架比较的共同 token、调用次数、成本或终止率数据，因此不能量化三类机制的相对效果。Anthropic findings 中约 15 倍 token 消耗是特定系统的报告，不应外推为通用成本系数。框架文档说明能力，不等同于具体部署的实测可靠性或安全性。

## 建议

- **按任务依赖拆分**：只委派边界清晰、可独立探索的子任务；强依赖或必须共享完整上下文的工作保留在同一流程中。
- **采用最小化、结构化交接**：规定目标、必要输入、输出字段、证据和完成状态；对授权或副作用相关字段在执行前校验，并按需过滤历史。
- **分层管理状态**：线程内连续性使用检查点，跨线程复用使用应用定义的长期存储；设置持久化后端、保留期限和清理策略。将关键计划与恢复信息外置。
- **设置应用层硬预算与明确终止条件**：按任务定义调用、时间或 token 上限；在每次交接前后检查剩余预算、任务状态和停止原因。不要把框架默认行为当作预算策略。
- **监控并审计**：记录子 Agent 输入/输出摘要、交接字段、调用次数、终止原因和状态规模；对关键结论保留可追溯依据，并抽查摘要是否遗漏重要证据。
- **按风险提高控制强度**：短时低风险任务可用轻量隔离和停止条件；长时、多阶段或有副作用的任务应增加权限校验、持久化恢复和硬预算边界。

## 局限性

本报告依据五个不同的官方页面，覆盖 LangChain Deep Agents、Anthropic、OpenAI Agents SDK、LangGraph 和 Microsoft AutoGen。Deep Agents 概览未展开子代理消息传递和窗口配置细节；OpenAI handoff 页面抓取内容有限；AutoGen 页面未核实 `max_turns` 的精确语义；Deep Agents filesystem 未取得可引用证据，因此不对其文件交接能力作事实性判断。缺少统一基准和部署实测数据，无法量化上下文隔离、状态交接或预算控制对成本、质量和失控率的因果影响。

## 参考资料

1. [Deep Agents overview — LangChain 官方文档](https://docs.langchain.com/oss/python/deepagents/overview)
2. [How we built our multi-agent research system — Anthropic 官方工程文章](https://www.anthropic.com/engineering/multi-agent-research-system)
3. [Handoffs — OpenAI Agents SDK 官方文档](https://openai.github.io/openai-agents-python/handoffs/)
4. [Persistence — LangGraph 官方文档](https://docs.langchain.com/oss/python/langgraph/persistence)
5. [Teams — Microsoft AutoGen 官方文档](https://microsoft.github.io/autogen/stable/user-guide/agentchat-user-guide/tutorial/teams.html)
