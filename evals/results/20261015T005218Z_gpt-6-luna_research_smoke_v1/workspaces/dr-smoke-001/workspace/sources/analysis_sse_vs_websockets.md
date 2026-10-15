# Analysis: SSE vs WebSockets for Browser-Based LLM Response Streaming

## Data sources

This comparison uses only the supplied findings:
- `/workspace/sources/findings_sse.md`
- `/workspace/sources/findings_websockets.md`
- `/workspace/sources/findings_llm_streaming.md`

No findings files were modified. No numeric calculations were needed.

## Comparison dimensions

The comparison covers directionality, browser API and request constraints, framing, reconnect/resumption, cancellation, authentication/security, infrastructure/operations, and suitable scenarios. Each section distinguishes documented facts from design implications.

## Key comparison

### Directionality

**Documented facts**
- SSE is a one-way server-to-client event stream over an HTTP response. Client messages are not carried by the SSE stream itself. (SSE findings; LLM streaming findings)
- WebSockets provide bidirectional messaging over a persistent connection. Browser code can send and receive messages. (WebSockets findings)

**Design implications**
- SSE naturally fits a response stream where the browser submits a prompt separately and then receives generated output. Stop, regenerate, tool input, and other client-to-server actions require a separate HTTP request or channel.
- WebSockets can carry generation requests, output deltas, and control messages on one connection. This can simplify interactive, ongoing two-way exchanges, but requires an application-level message protocol and lifecycle design.

### Browser API and request constraints

**Documented facts**
- Native `EventSource` opens a GET request from a URL and does not expose a request body, arbitrary headers, or a general method option. Credentials can be enabled, subject to CORS. (SSE findings)
- Browser `WebSocket` construction accepts a URL and optional subprotocols, not arbitrary request headers. Its API provides `send()`, message/lifecycle events, `readyState`, and `bufferedAmount`; it does not expose raw frame controls or a built-in stream-reader/backpressure interface. (WebSockets findings)
- `fetch()` with a streaming response reader is a documented implementation pattern when a POST body, custom authorization headers, or explicit request control is needed. (LLM streaming findings)

**Design implications**
- Native `EventSource` is convenient when the stream can be opened by URL and session/cookie authentication is suitable. For a typical prompt POST or bearer-token header, use a separate request to establish a stream, or use `fetch` and parse the response incrementally.
- WebSockets support client messages after connection establishment, but the browser handshake still does not allow arbitrary authorization headers. This does not eliminate the need to design authentication at connection setup and operation level.
- Neither browser API removes the need for application-side parsing, bounded queues, and rendering/memory management.

### Framing and application protocol

**Documented facts**
- SSE is UTF-8 text with `text/event-stream` framing. Fields such as `data`, `event`, `id`, and `retry` are line-oriented; a blank line dispatches an event, and multiple `data:` lines are joined. A comment line can serve as a non-dispatched keep-alive. (SSE findings; LLM streaming findings)
- WebSocket messages can contain text or binary data; protocol frames may fragment messages, but browser JavaScript receives complete messages through `message` events. The application defines the schema for deltas, completion, errors, and metadata. (WebSockets findings)
- LLM stream chunks/events are not necessarily one model token or one network chunk. Provider event schemas can be structured; Anthropic documents named SSE events with JSON data and lifecycle events. (LLM streaming findings)

**Design implications**
- SSE offers a standardized event envelope and is a natural fit for incremental text or structured events, provided the server correctly delimits events, flushes output, and defines terminal/error events.
- WebSockets offer flexible message payloads but require the application to define message types, sequencing, terminal states, and error semantics.
- For either transport, clients should parse incrementally at the protocol boundary and not assume transport chunk boundaries correspond to model-token boundaries.

### Reconnect and resumption

**Documented facts**
- `EventSource` reconnects automatically unless closed or told to stop. `retry:` can influence delay; `id:` updates last-event-ID state, which is sent as `Last-Event-ID` on reconnect. Actual replay/resumption requires server support and stable IDs; the mechanism alone does not guarantee exactly-once delivery. (SSE findings)
- The browser WebSocket API does not automatically reconnect or restore subscriptions, replay missed messages, or resume a generation. These are application responsibilities. A transport close does not establish whether generation completed or all updates were received. (WebSockets findings)

**Design implications**
- SSE provides useful reconnect mechanics, but reliable continuation still requires server-side event retention/replay, stable identifiers, and duplicate-safe client handling. Automatic reconnect should not be mistaken for generation resumption.
- WebSockets require explicit retry and recovery logic. The application should identify generations, query or reconcile state after interruption, and decide whether to restart or resume from a cursor.
- In both cases, define terminal events and idempotency/replay behavior before relying on recovery.

### Cancellation

**Documented facts**
- `EventSource.close()` closes the stream and prevents automatic reconnection. This stops client receipt, not necessarily server-side generation. (SSE findings)
- `AbortController.abort()` can abort a fetch request, response-body consumption, and streams. (LLM streaming findings)
- `WebSocket.close()` requests connection closure; a transport close does not itself establish the server-side generation outcome. (WebSockets findings)

**Design implications**
- A user-visible Stop action should be connected to server-side generation cancellation, not merely local stream closure. Define disconnect propagation and, where needed, a separate cancellation endpoint/message.
- With `fetch`, aborting is a direct browser-side control for the request/stream. With `EventSource`, close the subscription and separately cancel generation if required. With WebSockets, send an explicit cancel operation and/or close the connection, while ensuring the server interprets it correctly.
- Upstream compute and billing effects remain implementation/provider-dependent across these approaches.

### Authentication and security

**Documented facts**
- Native `EventSource` does not allow arbitrary request headers; cookie credentials are possible with the appropriate option and CORS configuration. (SSE findings)
- Browser WebSocket construction likewise does not allow arbitrary request headers. Findings describe secure `wss:`, origin validation, authentication/authorization, and risks of credentials in URLs or subprotocols. Cookie-authenticated sockets need protection against Cross-Site WebSocket Hijacking. (WebSockets findings)

**Design implications**
- Choose a credential flow compatible with browser API constraints. Avoid long-lived secrets in URLs; if a short-lived URL credential is used, tightly scope it and account for logging/telemetry exposure.
- Validate origins and authorize requested operations, not just the initial connection. Apply appropriate cookie policy and CORS/origin controls for the chosen transport.
- A `fetch`-based SSE client can send custom headers, but still requires normal HTTPS, authorization, and cross-origin policy design.

### Infrastructure and operations

**Documented facts**
- HTTP intermediaries may buffer or coalesce SSE output; the end-to-end path must flush bytes, and actual proxy/gateway/framework behavior must be tested. (LLM streaming findings)
- WebSockets use persistent connections that consume server/intermediary connection capacity. Idle timeouts and network changes can terminate them; heartbeat and timeout policy must align with infrastructure. Browser JavaScript cannot directly send protocol Ping frames. (WebSockets findings)
- WebSocket browser APIs do not provide built-in backpressure; outbound queues and slow consumers need application-level handling. (WebSockets findings)

**Design implications**
- SSE uses familiar HTTP response infrastructure, but streaming latency depends on buffering, flush behavior, and timeout configuration. Validate the deployed path rather than assuming immediate delivery.
- WebSockets may be operationally attractive for sustained bidirectional interaction, but require connection capacity planning, timeout/heartbeat coordination, and recovery handling.
- Both transports need bounded messages/queues and client rendering controls. The findings do not establish a universal operational cost or performance winner.

### Suitable scenarios

**Documented facts**
- Provider documentation in the supplied findings includes Anthropic streaming over SSE, with named events and JSON payloads. The findings do not establish a universal provider-independent transport recommendation. (LLM streaming findings)
- SSE is one-way; WebSockets are bidirectional. (SSE and WebSockets findings)

**Design implications**
- Prefer SSE (or `fetch` streaming with SSE parsing) when the primary requirement is server-to-browser generation output, HTTP request semantics are useful, and client controls can use separate requests. Native `EventSource` is most suitable when GET/URL and available credential mechanisms fit; use `fetch` streaming when POST bodies or custom headers are needed.
- Consider WebSockets when the assistant needs frequent, low-latency two-way messages over a persistent session—for example, ongoing interactive control or multiple event types in both directions—and the team is prepared to implement message schemas, reconnect/resumption, authorization, and operational controls.
- A hybrid design is also viable: ordinary HTTP for prompt submission and cancellation, with SSE for output; or WebSockets for interactive control where justified. The findings do not require a single transport for every assistant workflow.

## Conditional recommendation

For a browser-based assistant whose dominant workload is streaming generated responses to the user, use an HTTP-based stream—SSE where its event model fits, or `fetch` streaming when POST bodies/custom headers are required—as the default starting point. It aligns with the one-way output pattern and has documented provider precedent, while keeping prompt submission and cancellation as explicit HTTP operations.

Choose WebSockets when bidirectional, ongoing interaction is a core requirement rather than merely a convenience, and when the product can support the additional application-level work: message schema, authorization, heartbeat/timeout coordination, reconnect and state reconciliation, and slow-consumer handling. In either case, explicitly design terminal/error events, generation identifiers, cancellation propagation, and replay semantics; do not infer server-side completion or cancellation from a browser transport event alone.

## Data gaps and uncertainty

- The findings cite standards and provider documentation, but note that some primary-source pages were not directly retrieved during the underlying research. The comparison therefore reflects the supplied findings and is not an independent standards audit.
- Proxy buffering, timeout behavior, connection capacity, and browser implementation details are deployment-specific; no universal performance or cost comparison is supported by these inputs.
- Server-side cancellation, upstream generation termination, and billing effects are not guaranteed by either transport and depend on server/provider behavior.
- SSE event replay requires server implementation; WebSocket recovery is application-defined. Neither transport alone guarantees durable or exactly-once delivery.
- Provider-specific behavior is not universal. The supplied LLM findings document Anthropic SSE behavior but do not establish a cross-provider recommendation or current behavior for providers not covered there.
