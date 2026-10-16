# 多 Agent 深度调研系统的上下文与调用治理

## 背景

多 Agent 深度调研会把搜索、网页读取、文件处理和多轮推理分散到多个执行单元。若所有中间材料都留在主 Agent 的对话上下文中，工具输出和历史会持续累积；若子 Agent 自主调用工具或继续委派而没有边界，则可能出现无效循环、成本增长和难以审计的副作用。有效治理不是单一的“缩短提示词”，而是分别管理信息可见范围、状态传递和运行停止边界。

本报告依据 LangChain、LangGraph、OpenAI Agents SDK 与 Anthropic 的官方文档，讨论上下文隔离、文件/状态交接、预算与停止控制的互补关系。文档描述的是具体框架能力和设计建议，不代表所有多 Agent 系统都自动具备相同保障。

## 关键发现

1. **上下文隔离能把中间过程留在子 Agent 内，但依赖清晰的委派契约。** LangChain Deep Agents 的 `isolated` 模式只向子 Agent 提供被委派任务，主 Agent 接收最终结果而非全部中间工具调用；`fork` 则继承父级对话和系统提示，适用于确需上下文连续性的任务，但隔离较弱。[LangChain Deep Agents：Subagents](https://docs.langchain.com/oss/python/deepagents/subagents)
2. **文件/状态持久化与 handoff 解决不同问题。** LangGraph checkpointer 保存 thread 范围内的图状态，store 可保存跨 thread 的应用数据；OpenAI Agents SDK handoff 则转移控制权并传递输入。handoff 默认可能传递完整历史，需通过过滤或映射控制接收方上下文；持久化也不等于通用文件交接协议。[LangGraph Persistence](https://docs.langchain.com/oss/python/langgraph/persistence)；[OpenAI Agents SDK Handoffs](https://openai.github.io/openai-agents-python/handoffs/)
3. **有限轮数是硬停止边界，工具精简和结果压缩是软治理。** OpenAI Agents SDK 的 `max_turns` 可限制 Runner 轮数，超限会抛出 `MaxTurnsExceeded`；轮次边界取消提供额外停止入口。工具面精简、简洁回传和高信号输出可降低无效调用概率与上下文负担，但不能保证费用或时长封顶。[OpenAI Agents SDK：Running agents](https://openai.github.io/openai-agents-python/running_agents/)；[Claude Platform Docs：Define tools](https://platform.claude.com/docs/en/agents-and-tools/tool-use/define-tools)
4. **上下文控制不能替代权限与预算控制。** handoff 的可用性判断不等于对解析后参数的授权；副作用前仍需显式校验。现有核验页面也未提供统一的货币预算、端到端超时或通用循环检测方案。

## 证据与分析

### 机制比较

| 机制 | 控制对象 | 主要收益 | 取舍与失效模式 | 适用场景 |
|---|---|---|---|---|
| 子 Agent 上下文隔离（`isolated`） | 子 Agent 可见输入、主 Agent 承载的中间过程 | 将冗长搜索/工具过程留在子 Agent，主上下文只接收结论 | 关键背景或约束可能未传入；独立 system prompt 需重述必要规则；回传过度压缩会损害可核验性 | 多步、专业化、工具输出易膨胀且可清晰拆分的调研任务 |
| `fork` 上下文模式 | 父级历史的继承范围 | 保留对话连续性，减少重复说明 | 父级历史仍可能带来上下文负担，不能当作强隔离 | 子任务确实依赖父级对话细节或共享约束 |
| 文件/状态持久化 | 跨轮状态保存、恢复与复用 | 支持中断恢复、人机协作、容错及跨 thread 信息保存 | 内存后端重启可能丢失；checkpoint 累积增加存储/延迟；版本、并发、检索和权限需另行设计 | 长流程、可恢复任务、需要跨轮或跨会话复用状态 |
| handoff 与输入过滤 | 代理间控制权及接收方输入 | 可将任务交给专门代理，并筛选传递历史或元数据 | 默认完整历史可能增加上下文和敏感信息暴露；handoff 不替代应用状态或授权校验 | 代理职责切换、需要传递有限上下文的流程 |
| 轮数上限与取消 | Agent 运行继续推进的边界 | 可直接截断无界迭代，提供停止入口 | 达到上限时任务可能未完成；不等于费用上限或通用墙钟超时 | 多轮工具调用、handoff 链路或自主运行 |
| 工具面精简与结果压缩 | 工具选择歧义、单次返回噪声 | 降低无效调用概率和上下文膨胀 | 属于软性措施，不能保证调用次数、时长或费用上限 | 工具较多、返回冗长、需要主 Agent 快速整合的流程 |

### 组合逻辑

三类控制分别回答不同问题：上下文隔离回答“谁看到什么、主上下文保留多少过程”；文件/状态交接回答“必要状态如何跨轮保存和传递”；预算与停止控制回答“运行最多继续到什么边界”。因此，持久化不能替代停止条件，隔离也不能替代权限校验，简洁输出更不能替代硬预算。

建议采用分层治理：先定义子任务输入、工具范围、输出格式和完成条件；对不依赖父级历史的任务优先隔离，确需连续性时才传入必要上下文。子 Agent 回传简洁但可核验的结论，详细证据或中间工件通过稳定标识存放在文件/持久化层，避免反复搬运完整历史。handoff 接收方应只获得完成任务所需的历史或摘要，并在任何副作用前校验授权参数。

运行层应保留有限轮数上限和明确停止条件；若目标还包括费用或墙钟时长封顶，应在应用/编排层增加预算计量、截止时间和取消策略。停止时若需续跑，应与持久化状态设计配套。工具精简、结构化回传和高信号输出用于降低触发硬边界的概率，而不是替代硬边界。

### 证据强度与不确定性

官方文档直接支持具体机制：LangChain 描述隔离/fork、工具配置和结果回传；LangGraph 描述 checkpointer/store、checkpoint 生命周期及子图状态边界；OpenAI Agents SDK 描述 handoff 历史传递、过滤、授权检查时机和 Runner 轮数/取消；Anthropic 文档支持停止条件、工具面精简及高信号输出等设计原则。Anthropic 的《Building effective agents》也强调从简单方案开始、设置停止条件并测试防护。[Anthropic：Building Effective AI Agents](https://www.anthropic.com/engineering/building-effective-agents)

这些材料主要是机制说明和工程建议，没有提供跨框架实测、上下文节省比例、失控调用率或成本对照数据。因而可以判断控制机制的作用边界，但不能量化其效果，也不能推断某一配置必然避免失控。

## 建议

1. **为每次委派写清契约**：目标、必要输入、禁止事项、可用工具、输出结构、完成/停止条件；隔离模式下尤其要把不可缺少的系统约束显式传入。
2. **默认最小化上下文传递**：优先传任务摘要和必要证据，不默认转发完整历史；对敏感内容做过滤。回传应简洁、结构化且保留来源和关键依据，避免“短但不可验证”。
3. **把过程与持久状态分开**：短期运行状态用适当 checkpoint；跨轮复用信息放入有明确标识和访问规则的持久化存储。作为应用/架构层的实施建议，可为工件定义版本、保留、清理、并发更新和检索授权策略；这些并非本次核验文档已验证的框架保证。
4. **设置硬停止与应用级预算**：保留有限轮数上限，定义完成判据和取消路径；另行监控 token/费用、墙钟时间和重试次数，并在预算耗尽时停止或降级。轮数上限不能代替费用/时间预算；若因上限或取消而中止，应记录未完成状态，并按任务风险决定是否保存可恢复状态或转人工处理。
5. **将权限检查放在副作用之前**：不要把 handoff 是否启用视为参数授权；对解析后的参数、目标资源和操作权限进行校验，并记录拒绝与取消原因。
6. **按任务复杂度决定是否委派**：多步、专业化、上下文易膨胀的任务更适合子 Agent；简单任务或必须共享完整过程的任务，委派开销可能超过收益。

## 局限性

- 本报告使用的证据以官方产品文档和工程文章为主，未检索到跨框架独立基准或量化实验，无法给出上下文节省、成本下降或失控率改善的数值。
- 官方页面没有提供通用文件/工件交接协议、跨系统版本一致性、并发冲突解决、检索索引和完整权限审计方案；这些属于系统实现责任。
- 本次核验的运行文档未覆盖统一的 token/货币预算、端到端超时、重试上限或通用循环检测算法。不能将轮数上限或取消入口等同于完整预算治理。
- 不同框架的术语和实现边界并不完全相同；文档所述能力不能直接外推为所有多 Agent 系统的保证。

## 参考资料

以下均为本轮调研 findings 中记录的官方来源页面；按不同主机/路径计数，fragment 不用于区分来源：

1. [LangChain Deep Agents：Subagents](https://docs.langchain.com/oss/python/deepagents/subagents)
2. [LangGraph Persistence](https://docs.langchain.com/oss/python/langgraph/persistence)
3. [OpenAI Agents SDK：Handoffs](https://openai.github.io/openai-agents-python/handoffs/)
4. [OpenAI Agents SDK：Running agents](https://openai.github.io/openai-agents-python/running_agents/)
5. [Claude Platform Docs：Define tools](https://platform.claude.com/docs/en/agents-and-tools/tool-use/define-tools)
6. [Anthropic：Building Effective AI Agents](https://www.anthropic.com/engineering/building-effective-agents)
