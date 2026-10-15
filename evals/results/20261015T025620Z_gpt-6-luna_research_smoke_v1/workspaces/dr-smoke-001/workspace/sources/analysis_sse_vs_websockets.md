# Analysis: SSE vs. WebSockets for Browser-Based LLM Response Streaming

## Data sources

This comparison uses exactly the two existing evidence files requested:
- `/workspace/sources/findings_sse.md`
- `/workspace/sources/findings_websockets.md`

No `findings_llm_streaming.md` exists in the listed source directory, and no evidence from such a file is assumed. Findings were not modified. URLs below are limited to those already present in the two findings files.

## Calculation tasks

No numerical calculations are needed. No `structured_calculator` call was made.

## Comparison dimensions and key comparisons

### 1. Interaction model

**Sourced facts**
- SSE is a UTF-8, line-framed `text/event-stream`; blank lines dispatch events. The format supports `data`, `event`, `id`, and `retry` fields, and comment lines can serve as keep-alives. Native `EventSource` opens an HTTP GET stream. (SSE findings; W3C and MDN references below.)
- WebSocket provides a two-way channel after its opening handshake, allowing either endpoint to send messages independently. It is a transport rather than an LLM-specific event protocol; the application defines event types, ordering, completion, errors, and serialization. (WebSocket findings; secondary RFC overview and MDN below.)

**Engineering inference**
- For a one-way stream of generated text/events, SSE aligns naturally with the interaction pattern and has a standardized event framing model. WebSockets are a better fit when the assistant must exchange ongoing client actions and server output over the same live connection, such as interactive control during generation.
- SSE does not prevent a separate HTTP request from carrying user actions; it simply does not make the stream itself bidirectional.

### 2. Implementation complexity

**Sourced facts**
- Native `EventSource` handles SSE framing and reconnect behavior, but its request interface is limited to a URL and optional credentials setting. For POST prompts, custom authorization headers, or richer request control, the SSE findings recommend `fetch()` streaming with a response reader and application-side SSE parsing, or a fetch-based library.
- WebSocket exposes connection, send, and message-event APIs, but the application must define its message protocol and implement reconnect/resume behavior. The browser WebSocket API does not provide backpressure.

**Engineering inference**
- A simple GET-based SSE stream can require less application protocol machinery than WebSockets. SSE complexity rises if the product needs POST submission, custom headers, or custom retry behavior and therefore uses fetch-based parsing.
- WebSockets shift more responsibility to the application: message schema, lifecycle, retry, replay, and queue management. This can be justified when bidirectional interaction is a core requirement.

### 3. Authentication and request shape

**Sourced facts**
- Native `EventSource` cannot set a request body or arbitrary headers, including `Authorization: Bearer ...`; it uses GET. Its `withCredentials` option controls cross-origin credentials, and credentialed CORS requires compatible response headers and cannot use wildcard `Access-Control-Allow-Origin` with credentials. Same-origin cookie authentication is possible. The SSE findings caution that secrets in query strings can leak through logs and other URL-handling systems.
- WebSocket security findings recommend authenticating the connection, authorizing model/session actions, validating browser `Origin` against an allowlist where appropriate, and using `wss://`. Origin validation is not authentication or authorization. The findings do not establish a specific browser WebSocket mechanism for arbitrary authorization headers.

**Engineering inference**
- If the browser client must submit a prompt via POST or attach a bearer token, native `EventSource` alone is not a fit. Consider fetch-based SSE or a carefully designed cookie/session flow; avoid putting secrets in stream URLs.
- WebSockets can support an application-defined authenticated session, but the exact credential transport and lifecycle must be designed and verified for the chosen browser/server stack. Do not infer that WebSockets automatically solve credential handling.

### 4. Reconnect and resume

**Sourced facts**
- Native EventSource reconnects after a connection ends unless closed by the client or a non-retryable response condition applies. `retry:` can influence delay; `id:` updates the browser's last-event ID, which is sent as `Last-Event-ID` on reconnect. Replay is only possible if the application/server retains and consistently replays events; this does not guarantee exactly-once delivery.
- WebSocket is a live connection and the browser/API evidence does not promise automatic reconnection or missed-message recovery. The application must define retry and, if needed, resume/replay using IDs, sequence numbers, or cursors. Resuming a generation depends on server/model-serving architecture.

**Engineering inference**
- SSE provides a built-in reconnect-and-cursor convention, but durable resume still requires server-side event retention and replay logic. WebSocket requires more explicit reconnect and cursor design. Neither transport alone guarantees uninterrupted generation or exactly-once processing.

### 5. Flow control

**Sourced facts**
- The WebSocket findings state that the browser WebSocket API has no way to apply backpressure; fast incoming messages can cause buffering, memory use, or an unresponsive page. Application-level pacing, bounded queues, incremental processing, and cancellation are suggested. `WebSocketStream` is mentioned, but availability and production suitability should be checked.
- The SSE findings do not establish a comparable browser-level backpressure guarantee. They recommend fetch streaming for richer control but note that deployment behavior varies.

**Engineering inference**
- Do not treat SSE as automatically solving consumer overload. For either transport, measure and bound client-side buffering and define cancellation/pacing behavior. The evidence specifically documents the WebSocket API limitation; it does not support a definitive comparative claim that SSE has superior backpressure.

### 6. Infrastructure and operations

**Sourced facts**
- SSE deployment behavior such as proxy buffering, idle timeouts, compression, and connection limits varies by browser, network, and deployment. Heartbeats may be used to keep intermediaries from treating an idle stream as dead.
- WebSockets require infrastructure that supports persistent upgraded connections, lifecycle management, capacity planning, and observability. Proxies/load balancers, idle timeouts, network changes, and restarts may terminate connections. Heartbeats, graceful close, reconnect, and replay are operational concerns.

**Engineering inference**
- Both approaches need validation through the actual proxy, load balancer, hosting, and browser path. SSE uses ordinary HTTP streaming semantics but is not immune to buffering or timeouts; WebSockets add upgrade and persistent-connection lifecycle requirements. The evidence does not quantify operational cost or establish that one is universally easier to scale.

### 7. Security

**Sourced facts**
- SSE security/request considerations include CORS and credential configuration; query-string secrets risk exposure in logs and other URL-handling systems.
- WebSocket findings recommend `wss://`, authentication, authorization, and appropriate Origin validation. Origin checks do not replace authorization. The RFC-related source in the findings is secondary, and exact normative handshake requirements were not independently verified from an official RFC URL in this run.

**Engineering inference**
- Security depends more on correct identity, authorization, transport protection, and secret handling than on choosing a transport alone. For either option, authorize access to the specific generation/session and avoid treating connection establishment as permission to use a model or retrieve a conversation.

### 8. Suitable scenarios

**Engineering inference based on the sourced facts**
- **Prefer SSE / native EventSource** when the primary need is server-to-browser incremental output, a GET stream is acceptable, cookie-based authentication is suitable, and the built-in event/reconnect conventions are useful.
- **Prefer fetch-based SSE** when SSE framing is desirable but the client needs POST prompt submission, custom headers, or more control over cancellation and retry.
- **Prefer WebSockets** when the product needs frequent bidirectional messages on one connection—for example, interactive control or client actions interleaved with generated output—and the team can own protocol, reconnect, replay, and flow-control behavior.
- **Do not choose solely on presumed performance or scalability.** The supplied findings contain no comparative benchmark or deployment measurements.

## Calculation process

Not applicable: the requested comparison is qualitative and the supplied evidence contains no numerical dataset requiring calculation.

## Analysis conclusions

SSE is a strong default for a straightforward, predominantly one-way browser stream of LLM output, especially when native EventSource's GET, cookie, event framing, and reconnect conventions fit the application. Its main constraint is the native API's limited request shape; fetch-based SSE can address that at the cost of client-side framing and lifecycle work.

WebSockets are more suitable when bidirectional interaction is a first-class requirement. They provide a two-way channel, but the application must supply more of the protocol and reliability behavior, including reconnect/resume and overload handling. Neither transport guarantees durable generation resumption, exactly-once delivery, or deployment-independent behavior.

## Data gaps and uncertainty

- The evidence is limited to the two specified findings files; no `findings_llm_streaming.md` exists in the source directory listing, and no additional evidence was introduced.
- SSE claims are supported by a W3C Recommendation and an MDN EventSource reference (Spanish API page, as noted in the findings). Deployment-specific behavior is explicitly uncertain.
- WebSocket browser API claims are supported by MDN. The RFC-related source is a secondary overview, not an official RFC Editor result; detailed normative handshake/frame claims are therefore limited in the findings.
- The findings do not provide comparative latency, throughput, cost, browser-by-browser support, or production-scale measurements. No quantitative superiority claim is warranted.
- Recommendations about which scenario fits each transport are engineering inferences from the documented interaction and API characteristics, not direct benchmark findings.

## References

- [W3C Server-Sent Events Recommendation](https://www.w3.org/TR/2015/REC-eventsource-20150203/)
- [MDN EventSource API (Spanish)](https://developer.mozilla.org/es/docs/Web/API/EventSource)
- [RFC 6455 overview (secondary result)](https://websocket.xiniushu.com/)
- [MDN WebSocket API](https://developer.mozilla.org/en-US/docs/Web/API/WebSocket)
