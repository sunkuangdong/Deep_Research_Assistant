# AI Agent 公开模型方案与成本估算

## 背景

本报告比较两种可通过官方 API 公开使用、且官方资料显示具备 Agent 工作流相关能力的模型方案：OpenAI o3-mini 与 Anthropic Claude Sonnet 5.5。OpenAI 官方价格页将 o3-mini 描述为面向 coding、math、science 的小型高性价比推理模型，并列出 tools 与 Structured Outputs 支持；OpenAI 模型目录提供 Agents、工具及 API 模型文档入口。[OpenAI Pricing](https://openai.com/api/pricing/?utm_source=rachelandreago)；[OpenAI Models](https://developers.openai.com/api/docs/models)

Anthropic 官方模型目录将 Sonnet 5.5 定位为速度与智能的平衡方案，并说明模型支持工具使用；官方 API 定价文档列出其输入、输出单价。[Anthropic Models overview](https://platform.claude.com/docs/en/models/overview)；[Anthropic API Pricing](https://platform.claude.com/docs/en/about-claude/pricing)

## 价格证据

| 方案 | 官方页面所列基础输入价格 | 官方页面所列基础输出价格 | Agent 相关官方定位/能力 |
|---|---:|---:|---|
| OpenAI o3-mini | $1.10 / 百万 Token | $4.40 / 百万 Token | coding、math、science 优化；支持 tools、Structured Outputs；200k 上下文 |
| Claude Sonnet 5.5 | $2.00 / 百万 Token | $10.00 / 百万 Token | 速度与智能平衡；支持工具使用 |

OpenAI 价格来自官方 API 价格页；Anthropic 价格来自官方 Claude Platform API 定价页。两家页面均未在本轮可见内容中明确标注上述价格的发布日期或生效日期。报告运行日期为 **2026-10-14**，但这不是价格生效日期；价格应理解为本轮调研所见页面价格，不能据此确认其在该运行日期的历史有效性。OpenAI 搜索结果的发布时间元数据也不等同于价格生效日期。

## 计算与分析

### 计算口径

- 每日请求：10,000 次；每次平均输入 6,000 Token、输出 1,000 Token。
- 每日输入量：10,000 × 6,000 = 60,000,000 Token = 60 百万 Token。
- 每日输出量：10,000 × 1,000 = 10,000,000 Token = 10 百万 Token。
- 月成本按 30 天估算，金额均为美元。
- 公式：日成本 = 60（百万 Token）× 输入单价（美元/百万 Token）+ 10（百万 Token）× 输出单价（美元/百万 Token）；30 天月成本 = 日成本 × 30。

### 结果

| 模型 | 日输入费用 | 日输出费用 | 日总费用 | 30 天月总费用 |
|---|---:|---:|---:|---:|
| OpenAI o3-mini | $66 | $44 | **$110** | **$3,300** |
| Claude Sonnet 5.5 | $120 | $100 | **$220** | **$6,600** |

计算示例：o3-mini 日成本 = 60（百万 Token）× $1.10/百万 Token + 10（百万 Token）× $4.40/百万 Token = $66 + $44 = **$110/日**；30 天月成本 = $110 × 30 = **$3,300**。Sonnet 5.5 日成本 = 60 × $2 + 10 × $10 = **$220/日**；30 天月成本 = $220 × 30 = **$6,600**。

在相同 Token 负载下，Sonnet 5.5 的基础 Token 成本为 o3-mini 的 2 倍，差额为 $110/日、$3,300/30 天。该比较只反映给定单价与固定 Token 量的算术结果，不代表两模型质量、成功率或完成任务所需调用次数相同。

### 适用性与取舍

若 Agent 任务以 coding、数学或科学推理为主，且实测质量满足要求，o3-mini 可作为本负载下基础 Token 成本较低的候选；若更看重 Sonnet 5.5 在目标任务上的速度与能力平衡，可纳入同一任务集评测，但按本负载其基础 Token 费用为 o3-mini 的 2 倍。建议用代表性任务比较质量、延迟、工具调用成功率、重试率及实际 Token 消耗，再决定单模型或按任务复杂度路由。Anthropic 官方定价文档还说明 prompt caching 可降低重复上下文的成本与延迟；本次估算未计入缓存影响。

## 建议

1. 以 o3-mini 作为本负载下的基础 Token 成本基线，以 Sonnet 5.5 作为质量/速度对照，先进行同一批 Agent 任务的离线评测和小流量试运行。该建议仅基于给定单价和固定 Token 量，不代表整体性价比或模型优劣结论。
2. 预算应在基础 Token 费用之外考虑实际系统提示词、工具调用、多轮推理、重试、缓存写入/读取、税费及平台费用；上线前重新核对官方价格页。
3. 对重复上下文较多的工作流，单独测量缓存命中率与缓存计费后再估算实际成本；不要直接把本报告的基础费用当作完整账单预测。

## 假设与局限性

- **价格日期与变化风险：**报告运行日期为 2026-10-14。官方页面未显示上述价格的发布日期或生效日期，因此只能将其视为本轮调研所见页面价格，不能确认其在 2026-10-14 当日的历史有效性。价格可能随页面更新而变化，部署或采购前应重新核验官方报价。
- **负载假设：**每次请求固定平均 6,000 输入 Token、1,000 输出 Token；每天 10,000 次；月按 30 天。实际 Agent 常有多轮模型调用、工具结果回填和上下文增长，实际 Token 量可能更高。
- **费用范围：**仅按基础输入/输出 Token 单价计算；未计缓存折扣或缓存写入费、长上下文或特殊功能费、工具/第三方服务费、重试、税费、汇率、合同折扣及最低消费。
- **适用性证据：**模型定位来自厂商官方说明，不是独立性能基准；没有同一任务集的质量、延迟或单位任务成本数据，不能据此断言哪种模型整体更优。

### 参考资料（官方来源）

1. [OpenAI API Pricing](https://openai.com/api/pricing/?utm_source=rachelandreago)
2. [OpenAI Models](https://developers.openai.com/api/docs/models)
3. [Anthropic Models overview](https://platform.claude.com/docs/en/models/overview)
4. [Anthropic API Pricing](https://platform.claude.com/docs/en/about-claude/pricing)
