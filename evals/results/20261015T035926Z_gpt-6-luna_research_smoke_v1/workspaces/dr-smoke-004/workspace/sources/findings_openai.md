# Findings: OpenAI 公开可用模型方案与 Agent 适用性

## 调研范围
聚焦 OpenAI 官方 API 公开模型目录与 API 价格页，核实模型定位中与构建 AI Agent 相关的能力、可见的输入/输出价格，以及页面可见日期或价格生效日期。范围不包括 ChatGPT 订阅价格、第三方模型或工具调用的独立费用。

## 关键发现
- 官方模型目录将模型、Agents、Tools 等列为 API 文档的核心入口，并提供模型目录、模型选择与定价导航；目录页面还呈现 Responses API、Agents API、Agents SDK、工具连接等构建 Agent 的文档路径。这表明模型选择应结合工具调用与 Agent 编排能力，而非只按通用文本生成定位。来源：[Models | OpenAI API](https://developers.openai.com/api/docs/models)
- 官方价格页搜索摘要将 o1 定位为面向复杂、多步骤问题的推理模型，并明确支持 tools、Structured Outputs 和 vision，列出 200k 上下文；o3-mini 定位为面向 coding、math、science 的小型高性价比推理模型，也支持 tools 与 Structured Outputs，列出 200k 上下文。此类能力与需要多步推理、工具交互的 Agent 工作流相关。来源：[Pricing | OpenAI](https://openai.com/api/pricing/?utm_source=rachelandreago)
- 同一价格页将 GPT-4o 定位为处理复杂任务的高智能模型，GPT-4o mini 定位为较经济的小型模型；可作为通用任务与成本敏感任务的候选，但本轮搜索摘要未完整呈现其工具支持细节，不能据此断言具体 Agent 能力。来源：[Pricing | OpenAI](https://openai.com/api/pricing/?utm_source=rachelandreago)

## 价格证据
以下为官方价格页搜索结果明确显示的每 1M tokens 价格（美元）；价格页摘要未提供可核实的生效日期：

| 模型 | 输入 | 缓存输入 | 输出 | 页面定位/备注 |
|---|---:|---:|---:|---|
| o1 | $15.00 | $7.50 | $60.00 | 复杂、多步骤推理；支持 tools、Structured Outputs、vision；200k 上下文 |
| o3-mini | $1.10 | $0.55 | $4.40 | coding、math、science 优化；支持 tools、Structured Outputs；200k 上下文 |
| GPT-4o | $2.50 | $1.25 | $10.00 | 复杂任务的高智能模型；128k 上下文 |

来源：[Pricing | OpenAI](https://openai.com/api/pricing/?utm_source=rachelandreago)

## 证据与不确定性
- 价格页搜索结果标注发布时间为 2024-11-08T18:07:00Z，但这只是搜索结果的发布时间元数据，不等同于价格页的可见发布日期或价格生效日期。页面摘要没有显示生效日期；因此不能将该时间表述为价格生效时间。
- 价格页摘要只展示部分模型与价格，且未完整呈现 GPT-4o mini 价格，故未补录未被本轮官方结果明确显示的数值。价格可能随时间变化，引用时应以官方价格页当前内容为准。
- 模型目录页面成功抓取，返回的页面内容确认其为 OpenAI API 官方模型文档，并显示模型选择、Agents、工具等文档导航；抓取内容被截断，未能从正文核实具体模型条目的完整能力或日期。
- 本轮未发现官方页面明确标注价格生效日期。模型适用性结论限于官方页面摘要明确给出的定位与能力，不代表对特定 Agent 任务的性能评测。

## 参考来源
- [Pricing | OpenAI](https://openai.com/api/pricing/?utm_source=rachelandreago)
- [Models | OpenAI API](https://developers.openai.com/api/docs/models)
