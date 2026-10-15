# SSE vs WebSockets for Streaming LLM Responses in Browser-Based AI Assistants

## Background

Browser-based AI assistants need to deliver generated text and structured events incrementally, while also supporting prompt submission, cancellation, retries, and sometimes interactive control. Server-Sent Events (SSE) and WebSockets both support streaming, but they expose different communication models: SSE is a server-to-client event stream over HTTP, while WebSockets provide bidirectional messages over a persistent connection.

The choice is not simply about which transport is “faster.” It affects request shape, browser APIs, authentication, recovery semantics, infrastructure behavior, and how much application protocol the team must build. The relevant primary references include the [W3C Server-Sent Events Recommendation](https://www.w3.org/TR/2015/REC-eventsource-20150203/), the [WHATWG WebSockets Standard](https://html.spec.whatwg.org/multipage/web-sockets.html), and [RFC 6455](https://www.rfc-editor.org/rfc/rfc6455).

## Key Findings

- **SSE is a strong fit for one-way generated output.** It provides a standardized text event format over HTTP. The browser can receive incremental events while prompt submission and controls use separate requests.
- **Native `EventSource` has meaningful request constraints.** It opens a GET and does not expose arbitrary headers or a request body. For POST prompts or bearer-token headers, use `fetch()` with a streaming response reader, or establish a stream through a separate request and use an appropriate credential model.
- **WebSockets are appropriate when bidirectional interaction is central.** They allow client and server messages on one persistent connection, but the application must define message schemas, terminal/error semantics, authorization, reconnect behavior, and state recovery.
- **Neither transport guarantees durable delivery or server-side cancellation.** SSE reconnection and `Last-Event-ID` can support replay only when the server implements it. WebSocket reconnection and replay are application responsibilities. Closing or aborting the browser stream does not by itself prove that model generation or billing stopped.
- **Operational trade-offs are deployment-specific.** SSE depends on HTTP intermediaries flushing rather than buffering output. WebSockets require persistent-connection capacity and coordinated timeout/heartbeat handling. The evidence reviewed does not establish a universal performance or cost winner.

## Evidence and Analysis

### Protocol and browser API

SSE uses UTF-8 text with the `text/event-stream` media type. Fields such as `data`, `event`, `id`, and `retry` are line-oriented, and a blank line dispatches an event. This gives the application a standard event envelope for text deltas, metadata, errors, and completion markers. The [W3C specification](https://www.w3.org/TR/2015/REC-eventsource-20150203/) defines the parsing and reconnection model.

The native browser `EventSource` API is intentionally narrower than a general HTTP client: it opens a URL using GET and does not provide a request body or arbitrary request headers. This can be inconvenient for common LLM request patterns that submit a JSON prompt body or require an `Authorization` header. A `fetch()` request with an incrementally consumed response body is often a better fit for those cases; this is HTTP response streaming, not use of the native `EventSource` API, even when the response body uses SSE framing. Browser-side cancellation can use [`AbortController.abort()`](https://developer.mozilla.org/en-US/docs/Web/API/AbortController/abort).

WebSockets, specified by [RFC 6455](https://www.rfc-editor.org/rfc/rfc6455) and exposed in browsers through the [WHATWG WebSockets Standard](https://html.spec.whatwg.org/multipage/web-sockets.html), support bidirectional text or binary messages. Browser JavaScript receives complete messages and sends with `send()`, but the application defines its own message schema. The browser API does not expose arbitrary handshake headers or a built-in stream-reader/backpressure interface. Thus WebSockets offer more interaction flexibility, not a ready-made LLM event protocol.

### Recovery, cancellation, and security

`EventSource` automatically reconnects in applicable failure cases and can send `Last-Event-ID` when the server has supplied event IDs. This is a useful mechanism, not a guarantee of exactly-once delivery or generation resumption: the server must retain/replay events, and the client must handle duplicates. The browser WebSocket API does not automatically reconnect or restore missed messages; retry, replay, and state reconciliation must be implemented by the application.

For either transport, a transport close is not equivalent to a confirmed model cancellation. `EventSource.close()`, `WebSocket.close()`, or aborting a fetch stops or interrupts browser-side receipt, but upstream generation and billing depend on server/provider disconnect handling. A robust assistant should use generation identifiers, explicit terminal/error events, and a defined cancellation operation where needed.

Both native browser APIs constrain arbitrary authorization headers. SSE can use credentialed requests subject to CORS; WebSocket deployments need secure `wss:`, strict origin validation, authentication and authorization, and protection against cross-site WebSocket abuse when cookies are used. Avoid long-lived secrets in URLs because they may appear in logs or telemetry.

### Infrastructure and interaction pattern

SSE travels through HTTP infrastructure, but perceived streaming depends on the full path flushing output rather than buffering it. Reverse proxies, gateways, compression, and hosting platforms should be tested in the actual deployment. WebSockets keep connections open, so capacity, idle timeouts, heartbeat policy, and network interruption recovery need explicit operational treatment. Browser JavaScript cannot directly send WebSocket protocol Ping frames; application-level liveness mechanisms may be needed.

Provider documentation offers a concrete example rather than a universal rule: [Anthropic’s Messages streaming documentation](https://docs.anthropic.com/en/api/messages-streaming) describes streaming responses using SSE with named events and JSON data. This supports SSE as a practical provider pattern, but does not establish that every provider or assistant should use SSE.

Overall, SSE (or `fetch` streaming with SSE parsing) aligns with the common pattern of a prompt request followed by server-to-browser output. WebSockets are more compelling when the assistant needs frequent, ongoing two-way messages over a persistent session. Neither transport should be selected on an assumed universal latency or cost advantage; the reviewed evidence does not quantify one.

## Recommendations

1. **Default to HTTP streaming for response-centric assistants.** Use SSE when the event model and request constraints fit. Use `fetch()` streaming when the prompt must be sent in a POST body, custom headers are required, or explicit request cancellation/control is useful.
2. **Choose WebSockets for genuine bidirectional session needs.** Examples include frequent client control messages interleaved with output or a broader real-time interaction protocol. Do not adopt WebSockets solely to deliver generated text if ordinary HTTP streaming meets the requirement.
3. **Make recovery and cancellation explicit.** Define generation IDs, terminal/error events, duplicate handling, replay/resumption policy, and server-side cancellation propagation. Test what happens when the browser disconnects mid-generation.
4. **Validate the deployed path.** Measure time-to-first-event and interruption behavior through the actual proxy/gateway stack; verify SSE flushing or WebSocket timeout/heartbeat behavior, and test slow consumers and reconnects.
5. **Treat authentication as a design constraint.** Use HTTPS/WSS, avoid long-lived URL credentials, and apply CORS/origin checks and per-operation authorization appropriate to the chosen transport.

## Limitations

The comparison is based on protocol standards, browser API documentation, and the provider documentation identified below. The research did not independently verify every current browser implementation or provider-specific behavior. The SSE findings cite the W3C Recommendation and link to the current WHATWG section, but did not retrieve the living-standard page directly during research; the WebSocket findings likewise note that primary pages were not directly retrieved in the search results. These sources should be checked against current implementations before a production decision.

Proxy buffering, timeout behavior, connection capacity, and performance depend on deployment architecture; no universal latency, throughput, or cost winner is established here. Server-side cancellation and billing effects are provider- and implementation-dependent. Provider evidence includes Anthropic’s SSE contract but does not establish a cross-provider recommendation; no verified OpenAI primary streaming page was available in the research evidence.

### Sources

**Primary technical and provider sources**

- [W3C: Server-Sent Events Recommendation](https://www.w3.org/TR/2015/REC-eventsource-20150203/)
- [WHATWG HTML Living Standard: Server-sent events](https://html.spec.whatwg.org/multipage/server-sent-events.html)
- [RFC 6455: The WebSocket Protocol](https://www.rfc-editor.org/rfc/rfc6455)
- [WHATWG HTML Living Standard: WebSockets](https://html.spec.whatwg.org/multipage/web-sockets.html)
- [Anthropic API: Streaming Messages](https://docs.anthropic.com/en/api/messages-streaming)

**Browser API references**

- [MDN: WebSocket API](https://developer.mozilla.org/en-US/docs/Web/API/WebSocket)
- [MDN: AbortController.abort()](https://developer.mozilla.org/en-US/docs/Web/API/AbortController/abort)
