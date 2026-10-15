# Findings: SSE 与流式 LLM 响应
## 调研范围
仅覆盖浏览器原生 Server-Sent Events（SSE）接口及其对流式 LLM 响应的相关标准行为：EventSource 请求方法、事件流格式与媒体类型、重连和 Last-Event-ID、凭据与 CORS，以及由此产生的实现影响。不涉及与其他实时通信技术的广泛比较。

## 关键发现
- **原生 EventSource 仅提供 URL 与凭据模式选项，不提供请求方法、请求头或请求体配置。** WHATWG 的构造接口为 `new EventSource(url, { withCredentials })`；浏览器发起的连接使用 GET。MDN 也说明 EventSource 接收 URL 和可选 `withCredentials`，没有用于设置 POST 或自定义 Authorization/Content-Type 请求头的参数。因此，若 LLM 接口必须通过 POST 发送提示词/请求体，或必须设置自定义认证头，不能直接依赖原生 EventSource 发起该请求；需调整协议/认证设计，或使用可自行控制 HTTP 请求的客户端实现流解析。
  来源：[WHATWG HTML — Server-sent events](https://html.spec.whatwg.org/multipage/server-sent-events.html)、[MDN — EventSource](https://developer.mozilla.org/en-US/docs/Web/API/EventSource)
- **响应必须是 `text/event-stream`，事件以 UTF-8 文本行框定。** WHATWG 要求事件流使用 `text/event-stream` 媒体类型；流按行解析，空行触发事件派发。字段行采用 `field: value` 形式，常见字段包括 `data`、`event`、`id`、`retry`；注释行以冒号开头，可用于保持连接。多个 `data:` 行在派发时以换行符连接。对 LLM 输出，服务端应逐步写出完整的 SSE 字段行并以空行结束每个事件；仅发送任意文本块或 JSON 而不遵循 SSE framing，不会被 EventSource 按预期解析。流式响应应保持正确的 `Content-Type: text/event-stream`，并避免中间层缓冲导致事件迟迟不可见。
  来源：[WHATWG HTML — Parsing an event stream](https://html.spec.whatwg.org/multipage/server-sent-events.html#parsing-an-event-stream)、[MDN — Using server-sent events](https://developer.mozilla.org/en-US/docs/Web/API/Server-sent_events/Using_server-sent_events)
- **连接会自动重连；事件 ID 可用于恢复游标，但不等于应用层保证无重复/无丢失。** 连接意外关闭时，EventSource 会按其重连时间重新连接；`retry:` 可指定重连等待毫秒数。解析到 `id:` 字段后，浏览器更新最后事件 ID；后续重连请求会携带 `Last-Event-ID`。服务端可据此从相应位置继续发送，但必须自行实现事件持久化、游标解释及重复处理。若服务端希望终止重连，可按规范返回 HTTP 204；客户端调用 `close()` 也会关闭连接并阻止其继续重连。对一次性 LLM 生成，自动重连可能导致生成任务被重新订阅或重复输出，需设计稳定的生成 ID/事件 ID、恢复语义，或在完成后明确关闭流。
  来源：[WHATWG HTML — Reestablishing the connection / Last-Event-ID](https://html.spec.whatwg.org/multipage/server-sent-events.html)、[MDN — Using server-sent events](https://developer.mozilla.org/en-US/docs/Web/API/Server-sent_events/Using_server-sent_events)
- **跨源连接受 CORS 约束；跨源凭据需显式启用。** EventSource 默认不启用跨源凭据；设置 `{ withCredentials: true }` 后，跨源请求可携带凭据。服务端必须返回匹配的 `Access-Control-Allow-Origin`（不能在凭据模式下使用通配符 `*`）以及 `Access-Control-Allow-Credentials: true`。原生接口不能任意添加请求头；而凭据模式和 CORS 响应头仍须符合 Fetch/CORS 规则。使用 Cookie 会受到浏览器第三方 Cookie 策略等额外限制，不能仅凭 `withCredentials` 保证 Cookie 一定发送。
  来源：[WHATWG HTML — EventSource](https://html.spec.whatwg.org/multipage/server-sent-events.html)、[MDN — EventSource](https://developer.mozilla.org/en-US/docs/Web/API/EventSource)、[MDN — CORS](https://developer.mozilla.org/en-US/docs/Web/HTTP/CORS)
- **实用设计结论：** 原生 EventSource 适合浏览器以 GET 订阅一个可由 URL 标识的生成/事件流，并以 SSE 格式接收增量文本；提示词可通过先创建任务再订阅任务 URL 等方式传递，但应谨慎处理 URL 暴露与长度限制。若需要 POST 请求体、自定义认证头或更精细的请求控制，应采用可控的流式 Fetch 客户端并自行解析 SSE（或使用其他适配方案）。无论客户端如何实现，服务端都应明确事件边界、完成/错误事件、重连游标语义、缓存/代理缓冲策略及跨源策略。
  来源：[WHATWG HTML — Server-sent events](https://html.spec.whatwg.org/multipage/server-sent-events.html)、[MDN — Using server-sent events](https://developer.mozilla.org/en-US/docs/Web/API/Server-sent_events/Using_server-sent_events)

## 证据与不确定性
WHATWG HTML 是 EventSource 与事件流解析行为的规范性主要来源；MDN 用于补充面向浏览器开发者的接口和 CORS 说明。搜索服务本次返回限额错误，未能取得搜索结果；以上结论依据已知的规范/文档 URL 与其标准内容整理，未进行实时页面核验。浏览器对第三方 Cookie、代理缓冲、连接并发等实际行为可能受浏览器版本、隐私设置、部署链路影响；这些不改变 EventSource 的核心接口限制。SSE 的重连机制本身不定义应用层的 exactly-once 交付或 LLM 任务恢复语义，需由应用实现。

## 参考来源
- [WHATWG HTML — Server-sent events](https://html.spec.whatwg.org/multipage/server-sent-events.html)
- [MDN — Using server-sent events](https://developer.mozilla.org/en-US/docs/Web/API/Server-sent_events/Using_server-sent_events)
- [MDN — EventSource](https://developer.mozilla.org/en-US/docs/Web/API/EventSource)
- [MDN — Cross-Origin Resource Sharing (CORS)](https://developer.mozilla.org/en-US/docs/Web/HTTP/CORS)
- [RFC 9110 — HTTP Semantics, GET](https://www.rfc-editor.org/rfc/rfc9110.html#name-get)
