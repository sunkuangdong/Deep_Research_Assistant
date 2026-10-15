# Findings: OpenAI 官方流式响应文档
## 调研范围
仅核验 OpenAI 官方文档对 Responses API 和 Chat Completions 流式响应的明确说明，聚焦传输/事件格式、浏览器集成及文档所述注意事项。不扩展到其他提供商或非官方资料。

## 关键发现
- 本次尝试通过联网搜索定位 OpenAI 官方流式文档时，搜索工具返回“web_search 搜索预算已用完”，未提供任何搜索结果；因此无法据此核实官方页面正文，也不能将具体传输、事件格式、浏览器支持或 caveat 归因于官方文档。
  来源：本次 web_search 工具返回信息（无可用结果）。
- 待直接核验的官方文档入口包括 Responses API 流式指南及 Chat Completions API 参考。由于本次未能检索页面内容，以下仅列为待核验 URL，不代表已确认其当前可访问或页面具体陈述：
  - https://platform.openai.com/docs/guides/streaming-responses
  - https://platform.openai.com/docs/api-reference/chat/create

## 证据与不确定性
官方页面未能在本次调研中检索或读取，故无法确认页面当前内容、事件名称/载荷、SSE 或其他传输细节、浏览器集成方式及限制。以上 URL 是官方文档域名下的候选入口；本次没有成功取得页面正文，不能据此作实质性结论。应在可访问官方文档后再核验。

## 参考来源
- [OpenAI API 文档：Responses 流式指南（页面正文本次未能检索）](https://platform.openai.com/docs/guides/streaming-responses)
- [OpenAI API 参考：Chat Completions 创建（页面正文本次未能检索）](https://platform.openai.com/docs/api-reference/chat/create)
