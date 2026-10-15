# Findings: SSE 协议与浏览器运行时行为

## 调研范围

聚焦浏览器端使用 Server-Sent Events（SSE）接收 LLM 流式响应时的协议与运行时行为：事件流格式、单向通信、重连与 `Last-Event-ID`、浏览器 `EventSource` API 限制、凭据与 CORS，以及相关 HTTP 行为。不覆盖具体 LLM 服务商实现或其他流式协议。

## 关键发现

- **事件帧由 UTF-8 文本行构成，空行结束一个事件。** SSE 响应使用 `text/event-stream`；行可包含 `event`、`data`、`id`、`retry` 等字段，冒号开头的行是注释（常用于心跳）。多个 `data:` 行会以换行符拼接；空行触发派发，未以空行结束的尾部数据不会作为完整事件派发。字段名和值之间至多移除一个空格。规范还定义 CRLF、LF、CR 行结束符。来源：[WHATWG HTML Living Standard — Server-sent events](https://html.spec.whatwg.org/multipage/server-sent-events.html)

- **SSE 是服务器到客户端的单向事件通道。** `EventSource` 建立持久 HTTP 请求并接收事件；客户端不能通过该连接向服务器发送应用数据。浏览器端若需提交提示词或控制消息，需另用请求/通道。来源：[WHATWG HTML Living Standard — Server-sent events](https://html.spec.whatwg.org/multipage/server-sent-events.html)

- **连接中断后浏览器可自动重连，并携带事件游标。** `id:` 更新 EventSource 的最后事件 ID；重连请求会在适用时带 `Last-Event-ID` 请求头。`retry:` 可指定重连等待时间（毫秒，需为 ASCII 数字）；服务器可据此调整客户端重连间隔。重连语义不等于应用层保证无重复或恰好一次处理，客户端/服务端仍需设计幂等与游标恢复。来源：[WHATWG HTML Living Standard — Server-sent events](https://html.spec.whatwg.org/multipage/server-sent-events.html)

- **原生 `EventSource` API 的请求控制能力有限。** 构造器接受 URL 和可选 `withCredentials`；没有标准构造参数用于设置任意请求头、请求方法或请求体，因此原生接口适合 GET 型订阅，不适合直接在建立流的请求中携带自定义 Authorization 头或 POST body。可调用 `close()` 关闭连接；事件通过 `message` 或具名事件监听器接收。来源：[WHATWG HTML Living Standard — EventSource interface](https://html.spec.whatwg.org/multipage/server-sent-events.html)

- **跨源与凭据由 CORS 和 EventSource 凭据模式共同约束。** 默认跨源 EventSource 不启用凭据；`withCredentials: true` 请求凭据模式。跨源响应需满足 CORS 检查；带凭据时服务器必须返回明确的 `Access-Control-Allow-Origin`（不能用 `*`）并允许凭据（`Access-Control-Allow-Credentials: true`）。Cookie 的发送还受浏览器 Cookie 的 SameSite、第三方 Cookie 等策略影响。来源：[WHATWG HTML Living Standard — EventSource interface](https://html.spec.whatwg.org/multipage/server-sent-events.html)；[Fetch Standard — CORS protocol](https://fetch.spec.whatwg.org/#cors-protocol)

- **HTTP 响应需保持为可增量消费的事件流。** SSE 使用 `Content-Type: text/event-stream`；HTTP 传输层可分块/增量交付，但应用不能假设一次网络读取对应一个 SSE 事件帧。HTTP/1.1 chunked transfer coding 是传输分帧机制，不是 SSE 事件边界；HTTP/2/HTTP/3 也不应依赖 HTTP/1.1 的 chunked 编码。代理缓冲、压缩或中间层超时可能延迟可见数据，属于部署层行为，需端到端验证。来源：[WHATWG HTML Living Standard — Server-sent events](https://html.spec.whatwg.org/multipage/server-sent-events.html)；[RFC 9112 §7.1 — Chunked Transfer Coding](https://www.rfc-editor.org/rfc/rfc9112.html#section-7.1)；[RFC 9113 — HTTP/2](https://www.rfc-editor.org/rfc/rfc9113.html)

- **HTTP 状态与内容类型影响 EventSource 生命周期。** 规范定义成功响应的处理及重连/终止行为；例如 204 响应用于告知客户端停止重连。实现应返回正确的事件流媒体类型，并避免把普通 JSON 错当作 SSE。来源：[WHATWG HTML Living Standard — Server-sent events](https://html.spec.whatwg.org/multipage/server-sent-events.html)

## 证据与不确定性

主要依据 WHATWG HTML Living Standard、Fetch Standard 与 IETF HTTP 规范，属于协议/平台规范层面的事实。两次 `web_search` 均因搜索服务返回 403（配额不足）失败，因此未能通过搜索结果交叉核验；引用直接指向规范原文。代理缓冲、超时、压缩及浏览器对 Cookie 的具体限制会随部署配置、浏览器版本和隐私策略变化，不能仅由 SSE 规范推断。关于“无恰好一次保证”是对 SSE 游标/重连机制的工程含义，而非规范承诺。

## 参考来源

- [WHATWG HTML Living Standard — Server-sent events](https://html.spec.whatwg.org/multipage/server-sent-events.html)
- [Fetch Standard — CORS protocol](https://fetch.spec.whatwg.org/#cors-protocol)
- [RFC 9112 §7.1 — Chunked Transfer Coding](https://www.rfc-editor.org/rfc/rfc9112.html#section-7.1)
- [RFC 9113 — HTTP/2](https://www.rfc-editor.org/rfc/rfc9113.html)
