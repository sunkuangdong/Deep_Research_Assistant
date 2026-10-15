## Background

Browser-based AI assistants commonly submit a prompt and then render generated text incrementally. Two transport choices often considered are Server-Sent Events (SSE), a server-to-client event stream over HTTP, and WebSockets, a persistent full-duplex connection. The key decision is not simply whether output is streamed: it is whether the application needs one-way response delivery or ongoing bidirectional messaging, and how authentication, cancellation, recovery, and deployment constraints are handled.

This report distinguishes protocol/API facts from application-level implications. It also considers Fetch + ReadableStream as a practical browser option for request-driven LLM streaming; it is not a replacement name for SSE, but a way to consume an HTTP response stream with more request control.

## Key Findings

- **SSE is a natural fit for one-way event delivery.** It uses `text/event-stream`, supports named events and event IDs, and the browser’s EventSource can reconnect and send `Last-Event-ID` ([WHATWG HTML Living Standard](https://html.spec.whatwg.org/multipage/server-sent-events.html)). These mechanisms do not by themselves guarantee replay, exactly-once processing, or resumption of the same LLM generation.
- **WebSockets are justified by genuine bidirectional needs.** After the HTTP Upgrade handshake, client and server can send independently over a full-duplex connection ([RFC 6455](https://datatracker.ietf.org/doc/html/rfc6455)). This is useful for continuous upstream control or multiple interactive messages, but the browser API does not provide automatic reconnection or task-level recovery ([WHATWG WebSockets Standard](https://websockets.spec.whatwg.org/)).
- **For the common “submit once, stream the answer” pattern, Fetch + ReadableStream is often the most flexible starting point to evaluate.** Fetch supports request bodies and headers, and the client can abort the request/read using AbortController; this does not guarantee that server-side inference stops ([MDN: Using readable streams](https://developer.mozilla.org/en-US/docs/Web/API/Streams_API/Using_readable_streams); [MDN: AbortController](https://developer.mozilla.org/en-US/docs/Web/API/AbortController)). Native EventSource is simpler when its GET-oriented request shape and credential model fit; it does not expose arbitrary request headers or a request body ([WHATWG HTML Living Standard](https://html.spec.whatwg.org/multipage/server-sent-events.html)).
- **Neither transport solves application semantics.** Authentication, authorization, stopping server-side inference, deduplication, task recovery, and event replay must be designed explicitly.
- **Deployment behavior can dominate the choice.** HTTP streaming may be buffered or timed out by intermediaries; WebSockets require Upgrade and long-lived connection support. Validate the actual browser-to-service path rather than assuming one is universally faster or easier.

## Evidence and Analysis

### Protocol and browser API differences

| Dimension | SSE / EventSource | WebSocket |
|---|---|---|
| Direction | Server to browser; client sends application input separately ([WHATWG HTML](https://html.spec.whatwg.org/multipage/server-sent-events.html)) | Full duplex after connection establishment ([RFC 6455](https://datatracker.ietf.org/doc/html/rfc6455)) |
| Browser API | EventSource handles event framing and exposes message/named-event listeners; `close()` ends the stream ([WHATWG HTML](https://html.spec.whatwg.org/multipage/server-sent-events.html)) | `send()`, `message`, `close()`, connection states, and `bufferedAmount`; application defines message protocol ([WHATWG WebSockets](https://websockets.spec.whatwg.org/)) |
| Request setup | Native EventSource is GET-oriented and has no arbitrary headers/body constructor options; credentials can be enabled with `withCredentials` subject to CORS/cookie rules ([WHATWG HTML](https://html.spec.whatwg.org/multipage/server-sent-events.html); [Fetch Standard: CORS](https://fetch.spec.whatwg.org/#cors-protocol)) | Browser constructor accepts URL and optional subprotocols, not arbitrary handshake headers; handshake includes `Origin` for server validation ([WHATWG WebSockets](https://websockets.spec.whatwg.org/); [RFC 6455 §4](https://datatracker.ietf.org/doc/html/rfc6455#section-4)) |
| Reconnection | Standard EventSource reconnection and `id`/`Last-Event-ID` support ([WHATWG HTML](https://html.spec.whatwg.org/multipage/server-sent-events.html)) | Standard browser API has no automatic reconnect; application implements it ([WHATWG WebSockets](https://websockets.spec.whatwg.org/)) |
| Flow control | HTTP/stream consumption is incremental, but buffering depends on the full path | Classic browser WebSocket API lacks receive-side stream backpressure; `bufferedAmount` concerns queued outbound bytes ([WHATWG WebSockets](https://websockets.spec.whatwg.org/)) |
| Cancellation/close | `EventSource.close()`; Fetch streams can be aborted with AbortController ([WHATWG HTML](https://html.spec.whatwg.org/multipage/server-sent-events.html); [MDN: AbortController](https://developer.mozilla.org/en-US/docs/Web/API/AbortController)) | `WebSocket.close()`; closing transport does not itself define server task cancellation ([WHATWG WebSockets](https://websockets.spec.whatwg.org/)) |

SSE event boundaries are defined by the text event-stream format, not by network read or HTTP chunk boundaries ([WHATWG HTML](https://html.spec.whatwg.org/multipage/server-sent-events.html); [RFC 9112 §7.1](https://www.rfc-editor.org/rfc/rfc9112.html#section-7.1)). Likewise, WebSocket provides frames but does not define LLM token, tool-call, or conversation semantics ([RFC 6455](https://datatracker.ietf.org/doc/html/rfc6455)). Applications must parse the relevant protocol and handle partial delivery, errors, and completion explicitly.

### Trade-offs for LLM assistants

**Directionality and interaction model.** A typical turn sends one prompt and receives a stream of output. That pattern does not require a full-duplex socket: a POST request can submit the prompt while an HTTP response stream carries generated events. WebSocket becomes more compelling when the same connection must carry frequent upstream control or user messages while output is arriving—for example, a continuously interactive session. This is a fit judgment, not a claim that WebSockets are inherently faster.

**Request control and authentication.** Fetch can set headers and a body, making it suitable for POST-based generation and bearer-token authentication patterns. Native EventSource is convenient for a compatible GET subscription but cannot set arbitrary Authorization headers or a body. Browser WebSocket also lacks a general custom-header option in its standard constructor, so authentication must use a supported browser-safe design. In all cases, long-lived provider secrets should remain on a trusted server; Origin validation is not a substitute for authentication and authorization.

**Cancellation.** Fetch supports AbortController, and EventSource/WebSocket can be closed. These actions stop or close the client-side transport, but do not guarantee that server-side inference or other side effects stop immediately. If “Stop generating” must terminate work, define and verify a server-side cancellation operation or task state.

**Reconnection and recovery.** EventSource’s automatic reconnect and `Last-Event-ID` are useful transport-level features, but only if the server can associate IDs with retained/replayable events. They do not guarantee continuation of the same model generation. WebSocket reconnection is application-managed. For either transport, robust recovery requires task identifiers, sequence/cursor semantics, replay or status lookup, and duplicate handling. A reconnect is not equivalent to resuming a generation.

**Backpressure and resource management.** The classic browser WebSocket API does not provide receive-side backpressure driven by application consumption. Applications should bound message sizes and queues, control upstream send rates, and monitor outbound buffering. Fetch ReadableStream supports incremental consumption, but it does not eliminate buffering in browsers, networks, proxies, or application code.

**Infrastructure.** SSE and Fetch use HTTP response streaming, which may be affected by proxy buffering, compression, idle timeouts, or platform response limits. WebSockets require the deployment path to support the Upgrade handshake and long-lived connections, and may need heartbeat and reconnect policies. These are environment-specific constraints; protocol standards do not establish a universal deployment winner.

### Decision summary

- **Choose Fetch + ReadableStream first to evaluate** for a single prompt submission followed by streamed output, especially when POST bodies, custom headers, or explicit request cancellation are needed.
- **Choose EventSource/SSE** when the interface is naturally a one-way event subscription, its request and credential constraints fit, and native event parsing/reconnection are useful.
- **Choose WebSocket** when the product genuinely needs sustained bidirectional messaging on one connection, and the team can own authentication, flow control, reconnect/recovery, and long-connection operations.
- **For task-level recovery or strict delivery semantics**, specify the application protocol before choosing a transport; neither SSE nor WebSocket supplies those guarantees by itself.

## Recommendations

1. Model the interaction first: distinguish one request with streamed response from a continuously bidirectional session.
2. For ordinary chat turns, prototype Fetch + ReadableStream and compare it with the provider’s documented streaming interface. Use EventSource only when its GET-oriented API and credential behavior are compatible with the application.
3. Adopt WebSockets only for a concrete bidirectional requirement, not merely because the response arrives incrementally.
4. Keep provider credentials server-side or use a provider-supported short-lived/restricted credential mechanism. Validate CORS, cookies, and WebSocket Origin/authentication behavior in the actual browser setup.
5. Define cancellation, task IDs, replay/resume, deduplication, and error/completion events at the application layer. Test whether aborting or closing a connection actually stops server work.
6. Run end-to-end tests in the target deployment for first-event latency, incremental delivery, buffering, idle timeout, disconnect, reconnect, cancellation, and resource limits. Do not infer performance from protocol labels alone.

## Limitations

The research is based primarily on protocol and browser API documentation, including WHATWG, IETF RFCs, and the cited provider/platform documentation. The research agents reported that web search returned HTTP 403 due to quota limits, so current provider documentation pages and version-specific details were not independently verified during this run. No specific provider, browser support matrix, authentication architecture, proxy/CDN configuration, or recovery protocol was supplied. Consequently, this report makes no quantitative latency, throughput, or cost comparison and cannot determine which transport will perform best in a particular deployment. Provider-specific event schemas, credential options, and task-resumption support should be checked against the current official API documentation before implementation.

## References

- [WHATWG HTML Living Standard — Server-sent events](https://html.spec.whatwg.org/multipage/server-sent-events.html)
- [Fetch Standard — CORS protocol](https://fetch.spec.whatwg.org/#cors-protocol)
- [RFC 6455 — The WebSocket Protocol](https://datatracker.ietf.org/doc/html/rfc6455)
- [WHATWG WebSockets Standard](https://websockets.spec.whatwg.org/)
- [RFC 9112 §7.1 — Chunked Transfer Coding](https://www.rfc-editor.org/rfc/rfc9112.html#section-7.1)
- [OpenAI Responses API — Streaming](https://platform.openai.com/docs/guides/streaming-responses)
- [Anthropic Messages API — Streaming](https://docs.anthropic.com/en/api/messages-streaming)
- [MDN — Using readable streams](https://developer.mozilla.org/en-US/docs/Web/API/Streams_API/Using_readable_streams)
- [MDN — AbortController](https://developer.mozilla.org/en-US/docs/Web/API/AbortController)
- [AWS Lambda — Response streaming](https://docs.aws.amazon.com/lambda/latest/dg/configuration-response-streaming.html)
