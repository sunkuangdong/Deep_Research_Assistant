# Findings: 浏览器 AI 助手的应用层 LLM 流式模式与传输决策

## 调研范围

聚焦浏览器 AI 助手应用层的生成式响应流：token/事件流的消费、取消、双向交互、认证、断线恢复，以及部署/代理约束。区分协议与 API 文档明确规定的事实和实现建议；不比较未经证实的性能。联网搜索工具两次均因配额错误（HTTP 403）未返回结果，因此以下来源 URL 为已知官方文档入口，未能在本次运行中核验页面当前内容或具体版本。

## 关键发现

- **流式响应通常是服务端到客户端的事件流，不等于双向会话。** OpenAI Responses API 文档将流式输出描述为通过 SSE 接收事件；Anthropic Messages API 的流式模式也使用 SSE，并定义消息开始、内容块、增量、消息结束等事件。应用应按事件类型解析，而非假设每个网络块恰好对应一个 token 或完整事件；传输分块边界与应用事件边界并不相同。具体事件名称及字段应以所用 API 版本文档为准。  
  来源：[OpenAI Responses streaming](https://platform.openai.com/docs/guides/streaming-responses)、[Anthropic streaming messages](https://docs.anthropic.com/en/api/messages-streaming)

- **浏览器消费流可使用 Fetch 与 Streams API；取消可通过 AbortController。** Fetch 返回的响应体可作为可读流逐块读取，应用需处理解码、缓冲及流结束/错误；AbortController 可将 AbortSignal 传给 fetch 并中止请求。取消客户端读取/请求不应被表述为必然撤销服务端已完成的推理或副作用，服务端行为取决于 API 与部署链路。  
  来源：[MDN Using readable streams](https://developer.mozilla.org/en-US/docs/Web/API/Streams_API/Using_readable_streams)、[MDN AbortController](https://developer.mozilla.org/en-US/docs/Web/API/AbortController)

- **交互式助手的“用户输入上行 + 模型输出下行”通常需要应用层协调。** SSE 是单向服务器到客户端事件传输；若需要在同一实时连接上双向发送消息，应评估 WebSocket 或 WebRTC 等双向传输，或采用独立 HTTP 请求提交用户输入、SSE/Fetch 流接收响应的请求-响应模式。选择取决于是否需要持续双向消息、连接生命周期、基础设施支持及实现复杂度；不能仅凭“流式”一词推断双向能力。  
  来源：[WHATWG Server-sent events](https://html.spec.whatwg.org/multipage/server-sent-events.html)、[MDN WebSocket API](https://developer.mozilla.org/en-US/docs/Web/API/WebSockets_API)

- **认证与浏览器边界应纳入传输选择。** 浏览器端直接调用模型 API 会暴露客户端可访问的凭据风险；通常由受信任后端持有长期密钥并代理请求，或使用供应商明确支持的短期/受限凭据机制。Fetch 可设置请求头，但原生 EventSource 的接口对自定义请求头支持有限；若需 POST、Authorization 头或自定义请求体，Fetch 流或后端代理通常更适配。跨域请求还受 CORS 约束。具体可用认证方式须按供应商文档核实。  
  来源：[MDN EventSource](https://developer.mozilla.org/en-US/docs/Web/API/EventSource)、[MDN CORS](https://developer.mozilla.org/en-US/docs/Web/HTTP/CORS)、[OpenAI API authentication](https://platform.openai.com/docs/api-reference/authentication)

- **断线恢复不能默认等同于自动续传。** SSE 标准定义 `id`/`Last-Event-ID` 等重连机制，但应用或模型 API 是否提供可重放事件、稳定事件 ID、响应续传或幂等重试，需由具体 API 明确支持。若无明确恢复协议，客户端重试可能重新触发生成并产生重复成本/内容；建议将“重连”和“恢复同一生成”区分，并由应用维护请求标识、状态与重复提交策略。  
  来源：[WHATWG Server-sent events](https://html.spec.whatwg.org/multipage/server-sent-events.html)、[Anthropic Messages API](https://docs.anthropic.com/en/api/messages)

- **部署链路可能影响长连接与流式交付。** 反向代理、CDN、负载均衡器或 serverless 平台可能缓冲响应、设置空闲超时或限制连接时长；这些是部署配置/平台约束，不是 SSE 本身的保证。应核对所用平台的流式响应、超时、缓冲和连接限制，并在端到端环境验证首事件、增量交付、取消及断连行为。未找到可在本次搜索中核验的特定云平台官方限制，因此不列具体数值。  
  来源：[AWS Lambda response streaming](https://docs.aws.amazon.com/lambda/latest/dg/configuration-response-streaming.html)、[Cloudflare Workers Streams](https://developers.cloudflare.com/workers/runtime-apis/streams/)

- **传输决策建议（非性能结论）：** 若需求是单次请求后逐步显示文本，优先评估 Fetch + ReadableStream（便于 POST、请求头、AbortSignal 和自定义解析）；若需求是标准单向事件订阅且接口约束匹配，可评估 EventSource/SSE；若需要持续双向消息，则评估 WebSocket/WebRTC 或拆分上行请求与下行流。最终选择应以认证、跨域、代理支持、恢复语义、连接生命周期和供应商 API 形态为准，而非未经测量的速度判断。

## 证据与不确定性

本次 web_search 两次均因搜索配额不足返回 HTTP 403，未能检索或核验官方页面正文。上述内容依据所列标准/官方文档入口及通用 Web API 语义整理；OpenAI、Anthropic 当前事件字段、认证选项、恢复能力，以及云平台具体超时/缓冲限制均需在实施前查阅对应版本文档。SSE 的标准重连机制不意味着模型供应商支持生成任务续传；客户端 abort 也不保证服务端计算立即停止。未作性能优劣或延迟数字断言。

## 参考来源

- [OpenAI Responses API streaming guide](https://platform.openai.com/docs/guides/streaming-responses)
- [OpenAI API authentication](https://platform.openai.com/docs/api-reference/authentication)
- [Anthropic Messages API streaming](https://docs.anthropic.com/en/api/messages-streaming)
- [Anthropic Messages API](https://docs.anthropic.com/en/api/messages)
- [WHATWG HTML: Server-sent events](https://html.spec.whatwg.org/multipage/server-sent-events.html)
- [MDN: Using readable streams](https://developer.mozilla.org/en-US/docs/Web/API/Streams_API/Using_readable_streams)
- [MDN: AbortController](https://developer.mozilla.org/en-US/docs/Web/API/AbortController)
- [MDN: EventSource](https://developer.mozilla.org/en-US/docs/Web/API/EventSource)
- [MDN: CORS](https://developer.mozilla.org/en-US/docs/Web/HTTP/CORS)
- [MDN: WebSocket API](https://developer.mozilla.org/en-US/docs/Web/API/WebSockets_API)
- [AWS Lambda response streaming](https://docs.aws.amazon.com/lambda/latest/dg/configuration-response-streaming.html)
- [Cloudflare Workers Streams](https://developers.cloudflare.com/workers/runtime-apis/streams/)
