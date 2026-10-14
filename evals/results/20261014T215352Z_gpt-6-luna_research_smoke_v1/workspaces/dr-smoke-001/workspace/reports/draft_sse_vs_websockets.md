## Background

Browser-based AI assistants commonly submit a prompt and then render incremental model output. Server-Sent Events (SSE) and WebSockets can both carry that output, but they differ in directionality, browser APIs, recovery behavior, and infrastructure requirements. The key design question is not simply how to stream text; it is whether the application needs a one-way response stream or a sustained bidirectional session.

This report draws on protocol and browser documentation, including the WHATWG HTML and WebSockets standards, RFC 6455, MDN, and official LLM API documentation. It distinguishes documented transport behavior from application-level recommendations.

## Key Findings

1. **SSE is a strong fit for one-way response delivery as a design choice, not a universal performance winner.** Native `EventSource` receives a UTF-8 `text/event-stream` and supports named events, event IDs, and reconnection behavior. It is a natural shape for deltas, lifecycle events, and completion markers. Its reconnection mechanism does not itself guarantee replay or exactly-once delivery ([WHATWG HTML](https://html.spec.whatwg.org/multipage/server-sent-events.html)).
2. **WebSockets are appropriate when bidirectionality is a real requirement.** A persistent full-duplex connection lets the browser send controls while the server streams output. This is useful for real-time audio, interactive interruption, or multiplexed sessions, but requires an application-defined event protocol and recovery behavior ([RFC 6455](https://www.rfc-editor.org/rfc/rfc6455); [OpenAI Realtime API guide](https://platform.openai.com/docs/guides/realtime)).
3. **For ordinary authenticated prompt-to-response flows, fetch-based SSE can be more practical than native `EventSource`.** Fetch supports request bodies, headers, and abort signals; native `EventSource` has limited request customization ([MDN EventSource](https://developer.mozilla.org/en-US/docs/Web/API/EventSource); [MDN Fetch API](https://developer.mozilla.org/en-US/docs/Web/API/Fetch_API); [MDN AbortController](https://developer.mozilla.org/en-US/docs/Web/API/AbortController)). Fetch does not automatically parse SSE or inherit `EventSource` reconnection and `Last-Event-ID` behavior: the client must parse the event stream and implement any desired reconnect/resume policy. The browser WebSocket constructor also has constraints around arbitrary headers ([MDN WebSocket](https://developer.mozilla.org/en-US/docs/Web/API/WebSocket)).
4. **Transport boundaries are not model-token boundaries.** Applications should parse SSE events or WebSocket messages and handle arbitrary deltas, structured events, errors, and explicit completion semantics ([OpenAI Responses API streaming](https://platform.openai.com/docs/guides/streaming-responses); [Anthropic streaming messages](https://docs.anthropic.com/en/api/messages-streaming)).
5. **Neither transport alone guarantees end-to-end cancellation, application-level replay, or recovery after disconnection.** Cancellation must propagate to upstream model work; recovery requires application state/cursors; production proxy and timeout behavior must be tested.
6. **WebSocket receive-side backpressure is a browser API concern.** The standard browser API does not provide receive-side backpressure ([MDN WebSocket](https://developer.mozilla.org/en-US/docs/Web/API/WebSocket)). SSE and HTTP streaming also require realistic testing for buffering and resource behavior; no universal performance winner is established by the sources reviewed.

## Evidence and Analysis

| Dimension | SSE | WebSockets | Implication for LLM assistants |
|---|---|---|---|
| Directionality | Native `EventSource` is server-to-browser. Client input uses another request/channel. | Persistent full-duplex communication. | SSE fits prompt submission followed by output; WebSockets fit ongoing client controls or interactive sessions. |
| Browser request model | Native `EventSource` does not expose a general POST body or arbitrary headers. Fetch-based SSE parsing does. | Browser API supports `send()`, but the constructor does not expose arbitrary request headers. | Use fetch + SSE parsing for authenticated POST requests; use a backend proxy or suitable short-lived/cookie-based auth pattern for either transport. |
| Framing and semantics | UTF-8 event stream with defined fields and event delimiters. | Generic text/binary messages; application defines event schema. | Neither transport maps network chunks or frames to model tokens. Define delta, completion, error, and metadata events explicitly. |
| Reconnection | Native `EventSource` reconnects and can send `Last-Event-ID`; server must implement replay/deduplication. | Reconnect and resume are application responsibilities. | Built-in reconnect is not equivalent to guaranteed recovery. Use explicit cursors and server-side state if resumption matters. |
| Cancellation | Fetch can be aborted; `EventSource` can be closed. | Send an application cancel event or close the connection. | Propagate cancellation through the application server to the provider; a client disconnect alone does not prove generation stopped. |
| Flow control | Actual buffering/flush behavior depends on implementation and infrastructure. | Browser API lacks receive-side backpressure; incoming messages can accumulate if processing lags. | Bound processing and test under load; WebSocket applications may need application-level pacing. |
| Infrastructure | Uses HTTP responses, but intermediaries may buffer or time out streams. | Requires WebSocket upgrade/tunnel support and may face platform-specific limits. | Test the actual CDN, proxy, load balancer, runtime, and corporate network path. |
| Security | Native `EventSource` has limited header control; fetch supports headers. | Browser constructor has limited header control; origin validation and per-operation authorization remain necessary. | Keep provider secrets and privileged tool execution server-side; do not treat transport choice as authorization. |

The standards establish protocol and browser API behavior, not comparative latency or reliability. The recommendation to prefer SSE for conventional one-way generation and WebSockets for sustained bidirectional interaction is a design inference from those behaviors, not a universal performance claim. Official provider documentation illustrates both patterns: OpenAI and Anthropic document SSE-style response streaming, while OpenAI's Realtime API uses WebSockets for real-time interaction.

## Recommendations

- **Default to SSE for conventional text generation** when the interaction is prompt submission followed by server-to-browser output. Prefer **fetch-based SSE parsing** when the request needs a POST body, custom authorization headers, or abort control.
- **Use native `EventSource`** when its URL-based request model and credential options fit, and built-in reconnection is useful. Do not assume it can send arbitrary headers or a POST body.
- **Choose WebSockets** when the browser must send frequent controls during generation, or the product needs real-time audio, multiplexed events, or a persistent bidirectional session. Do not choose it solely because output is streamed.
- For either transport, define explicit event/message schemas, completion and error signals, cancellation propagation, and any replay/resume cursor. Do not infer completion from silence or connection closure.
- Test streaming flush behavior, buffering, idle timeouts, reconnects, and resource use through the production network path. For WebSockets, plan for receive-side processing limits and application-level flow control.
- Keep provider credentials and privileged tool execution on a trusted backend where possible; authenticate sessions and authorize each operation independently of transport.

## Limitations

No comparative benchmark evidence was found for latency, throughput, cost, or reliability, so this report does not claim that either transport is categorically faster or more reliable. Proxy buffering, idle timeouts, WebSocket upgrade support, connection duration, and scaling behavior are deployment-specific. Browser limits and implementation details can vary. Provider event names, cancellation propagation, and replay behavior may change and should be checked against current documentation and the target implementation. The research notes report that live search results were unavailable during their research runs; the cited primary documentation URLs should therefore be verified during implementation.

### Sources

- [WHATWG HTML Living Standard — Server-sent events](https://html.spec.whatwg.org/multipage/server-sent-events.html)
- [WHATWG WebSockets Standard](https://websockets.spec.whatwg.org/)
- [RFC 6455: The WebSocket Protocol](https://www.rfc-editor.org/rfc/rfc6455)
- [MDN: EventSource](https://developer.mozilla.org/en-US/docs/Web/API/EventSource)
- [MDN: Using server-sent events](https://developer.mozilla.org/en-US/docs/Web/API/Server-sent_events/Using_server-sent_events)
- [MDN: WebSocket](https://developer.mozilla.org/en-US/docs/Web/API/WebSocket)
- [MDN: AbortController](https://developer.mozilla.org/en-US/docs/Web/API/AbortController)
- [OpenAI Responses API streaming](https://platform.openai.com/docs/guides/streaming-responses)
- [OpenAI Realtime API guide](https://platform.openai.com/docs/guides/realtime)
- [Anthropic streaming messages](https://docs.anthropic.com/en/api/messages-streaming)
- [OWASP WebSocket Security Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/WebSocket_Security_Cheat_Sheet.html)
- [Cloudflare WebSockets](https://developers.cloudflare.com/network/websockets/)
- [AWS API Gateway WebSocket APIs](https://docs.aws.amazon.com/apigateway/latest/developerguide/apigateway-websocket-api.html)