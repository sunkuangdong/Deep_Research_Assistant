# Findings: Anthropic 官方 API 定价专页

## 调研范围
核验 Anthropic 官方 Claude Platform 文档中的 API 定价专页（区别于模型目录及 claude.com 订阅价格页），重点记录模型 API 输入/输出单价、页面是否标注价格日期或生效日期，以及适用于 Agent 的官方说明。

## 关键发现
- 已成功抓取 Anthropic 官方 Claude Platform Docs 的定价专页；页面标题为“Pricing”，正文说明其提供模型与功能的详细定价，价格以美元计。该页面是 API/平台定价资料，而非 claude.com 的消费者订阅价格页。
来源：[Pricing - Claude Platform Docs](https://platform.claude.com/docs/en/about-claude/pricing)
- 页面列出的代表性模型基础 token 单价（每百万 token，MTok）：Claude Opus 5.5 输入 $4、输出 $20；Claude Sonnet 5.5 输入 $2、输出 $10；Claude Haiku 5.5 输入 $0.10（提示不超过 100,000 tokens）/ $0.50（超过 100,000 tokens）、输出 $0.50 / $2.50（对应长上下文档位）。页面还列出 Claude Fable 5.1 输入 $10、输出 $50。以上为页面抓取时显示的价格；不同模型及功能可能有不同计费规则。
来源：[Pricing - Claude Platform Docs](https://platform.claude.com/docs/en/about-claude/pricing)
- 页面未显示明确的“价格发布日期”或“生效日期”。因此只能确认抓取时页面所列价格，不能据此断言其首次发布或生效时间。
来源：[Pricing - Claude Platform Docs](https://platform.claude.com/docs/en/about-claude/pricing)
- 页面对 Agent 的官方定位包括：Claude Fable 5.1 适用于“demanding reasoning and long-horizon agentic work”；Claude Opus 5.5 适用于“long-running agentic coding and knowledge work”。这属于官方模型用途说明，不等同于对所有 Agent 工作负载的性能或成本保证。
来源：[Pricing - Claude Platform Docs](https://platform.claude.com/docs/en/about-claude/pricing)
- 页面说明 Prompt caching 可在 API 调用间复用已处理的 prompt 内容，降低成本与延迟；自动缓存是多数用例的推荐起点。对重复发送大型 system prompt、文档或对话历史的 Agent 工作流，这一官方说明具有直接相关性。页面还列出缓存写入/读取相对基础输入价格的倍率。
来源：[Pricing - Claude Platform Docs](https://platform.claude.com/docs/en/about-claude/pricing)

## 证据与不确定性
本轮搜索未返回官方原始 API 定价页面的搜索结果；但通过 web_fetch 成功读取并验证了 Anthropic 官方定价专页，故已检索到官方原始页面。抓取内容明确给出模型输入/输出单价及 Agent 用途说明，但未见价格日期或生效日期。页面内容可能随时间更新，所列价格应视为本轮抓取时页面呈现值，而非带有明确生效时间的历史价格记录。

## 参考来源
- [Pricing - Claude Platform Docs](https://platform.claude.com/docs/en/about-claude/pricing)
