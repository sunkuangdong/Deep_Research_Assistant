# Findings: Anthropic 公开可用模型方案

## 调研范围
聚焦 Anthropic 官方模型目录中公开列出的 Claude 模型定位，以及官方 API 按输入、输出 token 计价的价格信息。重点关注适合构建 AI Agent 的模型用途，并核实价格页可见日期或生效日期。未覆盖第三方云平台价格、订阅套餐价格及工具调用等附加费用。

## 关键发现
- 官方模型目录将 Claude Fable 5.1 定位为适用于高难度推理和长周期 Agent 工作；Claude Opus 5.5 适用于长时间运行的 Agent 编码与知识工作；Claude Sonnet 5.5 强调速度与智能的综合平衡；Claude Haiku 5.5 面向分类、抽取、路由等高吞吐、低延迟任务。目录说明当前模型均支持文本和图像输入、文本输出、多语言、视觉及工具使用。
  来源：[Anthropic Models overview](https://platform.claude.com/docs/en/models/overview)
- 对 Agent 架构选型而言，官方定位支持按任务复杂度分层：长周期、高难度推理可优先评估 Fable 或 Opus；需要速度与能力平衡可评估 Sonnet；高频、低延迟的子任务可评估 Haiku。此为依据官方用途描述作出的选型归纳，不代表独立性能测试结论。
  来源：[Anthropic Models overview](https://platform.claude.com/docs/en/models/overview)
- 模型目录列出的 API 价格（每百万 token）：Fable 5.1 输入 $10、输出 $50；Opus 5.5 输入 $4、输出 $20；Sonnet 5.5 输入 $2、输出 $10；Haiku 5.5 起价输入 $0.10、输出 $0.50。目录未在抓取内容中显示价格生效日期。
  来源：[Anthropic Models overview](https://platform.claude.com/docs/en/models/overview)

## 价格证据
- 本轮抓取 Anthropic 官方价格页请求后，工具成功返回的规范页面 URL 为 `https://claude.com/pricing`，但页面内容主要呈现个人及团队订阅方案，未能在返回内容中核实 API 模型输入/输出价格或价格生效日期。因此不将该页作为 API 单价证据。
  来源：[Anthropic Pricing](https://claude.com/pricing)
- API 单价证据来自官方模型目录的模型比较表，单位明确为 input/output MTok（每百万 token）。抓取内容未提供价格页可见日期、更新时间或生效日期；因此不能据此断言价格自某日生效。价格可能随页面更新而变化，引用时应以官方页面当前展示为准。
  来源：[Anthropic Models overview](https://platform.claude.com/docs/en/models/overview)

## 证据与不确定性
本轮搜索未返回所需官方页面，随后对官方价格页和模型目录进行抓取验证。模型目录抓取内容提供了模型定位及 API 单价，但没有可见发布日期/生效日期；官方价格页抓取内容未呈现 API 单价。故模型定位和目录所列价格有官方页面证据，但价格日期无法核实。模型名称及价格反映本轮抓取时页面内容，不应视为长期固定报价。

## 参考来源
- [Anthropic Pricing](https://claude.com/pricing)
- [Anthropic Models overview](https://platform.claude.com/docs/en/models/overview)
