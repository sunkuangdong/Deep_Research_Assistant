# Analysis: SSE vs WebSockets for Browser-Based LLM Response Streaming

## Data sources

Used exactly the following findings files, as requested:
- `/workspace/sources/findings_sse.md`
- `/workspace/sources/findings_websockets.md`
- `/workspace/sources/findings_llm_streaming.md`

No other files were used as evidence. No numerical calculations were needed.

## Analysis dimensions

1. Directionality and interaction pattern
2. Browser API ergonomics and request control
3. Event/message framing and LLM stream semantics
4. Cancellation, completion, and recovery
5. Backpressure and resource management
6. Authentication and security considerations
7. Infrastructure compatibility and operational behavior
8. Suitable application scenarios

## Key comparison and trade-offs

| Dimension | SSE | WebSockets | Practical implication |
|---|---|---|---|
| Communication direction | Native `EventSource` is server-to-browser; client input requires a separate request/channel. | Persistent full-duplex channel; either endpoint can send messages independently. | SSE fits a request followed by streamed output. WebSockets fit sessions where client controls or inputs continue during generation. |
| Browser request ergonomics | Native `EventSource` does not expose a general request body or arbitrary headers. Fetch-based streaming can provide POST bodies, headers, and abort control, but requires client-side stream parsing. | Browser API supports `send()` but its constructor does not expose arbitrary request headers. | For authenticated POST-based generation, fetch + SSE parsing may be more practical than native `EventSource`; WebSockets also need an authentication pattern such as cookies, short-lived tickets, or a backend proxy. |
| Stream framing | UTF-8 `text/event-stream`; events are delimited by SSE rules, with named events and fields such as `data`, `id`, and `retry`. | WebSocket messages can be text or binary; protocol frames may be fragmented, and browser APIs expose reassembled messages rather than raw frame boundaries. | Neither network reads, protocol frames, nor messages should be assumed to equal model tokens. Parse application events/messages and handle arbitrary fragments. |
| LLM event semantics | Named/data events naturally represent deltas, completion, usage, and lifecycle events. | Transport is generic; the application must define event types, framing, ordering, errors, and completion semantics. | SSE offers a conventional event-stream shape; WebSockets offer flexibility but require an explicit application protocol. Both need application-level semantics. |
| Reconnection and recovery | `EventSource` has built-in reconnection behavior; `id`/`Last-Event-ID` can provide a resume cursor if the server implements replay or deduplication. This does not guarantee replay or exactly-once delivery. | The browser API does not provide equivalent application-level replay semantics; reconnect/resume policy and cursors must be designed by the application. | SSE has a built-in reconnection signal, not guaranteed recovery. Either transport needs server-side state and explicit recovery semantics if missed events matter. |
| Cancellation and completion | Fetch streams can be aborted; `EventSource` can be closed. Disconnecting alone does not prove upstream generation stopped. | Client can send an application-defined cancel/interrupt message or close the socket. Closing a shared session may discard unrelated state. | Propagate cancellation through UI, application server, and provider. Use explicit completion/error events rather than inferring completion from silence or connection closure. |
| Backpressure | Findings do not establish a universal receive-side backpressure guarantee for SSE; buffering and timely flushing depend on implementation and infrastructure. | Standard browser `WebSocket` API has no receive-side backpressure; incoming messages can accumulate if processing lags. `bufferedAmount` concerns outgoing queued bytes only. | WebSocket applications should consider pacing/flow control and bounded processing. For either transport, test memory and buffering behavior under realistic load. |
| Infrastructure | Uses HTTP responses and may be easier to route through HTTP infrastructure, but proxies/CDNs/servers can buffer, time out, or close streams. | Requires WebSocket upgrade/tunnel support and may face platform-specific duration, idle-timeout, or scaling constraints. | Compatibility is deployment-specific. Test the actual CDN, proxy, load balancer, runtime, and corporate network path. Neither transport guarantees low latency or uninterrupted delivery. |
| Security and authentication | Native `EventSource` has limited header configuration; fetch can attach headers. Cross-origin credential behavior is subject to browser rules. | Browser constructor also lacks arbitrary headers. Authentication, origin validation, and per-operation authorization remain application responsibilities. | Avoid long-lived secrets in URLs. A backend proxy can centralize credentials, policy enforcement, and provider event normalization. CORS alone is not WebSocket authorization. |

## Facts vs. inferences

### Documented facts in the findings

- SSE is a unidirectional server-to-browser event stream in the native browser `EventSource` API, with defined event framing and reconnection-related fields.
- `Last-Event-ID` can be sent on reconnection, but replay, deduplication, and exactly-once behavior depend on application/server implementation.
- WebSockets provide a persistent full-duplex channel. The browser API sends and receives messages, exposes lifecycle events, and does not provide receive-side backpressure.
- WebSocket protocol frames/messages and SSE events do not define model-token boundaries. Provider streams can include deltas and structured lifecycle events beyond plain text.
- Browser API constraints affect authentication and request customization for both native `EventSource` and WebSocket; fetch-based streaming offers more request control.
- Cancellation, completion semantics, replay, and proxy behavior require application/deployment handling; neither transport alone guarantees end-to-end cancellation or recovery.

### Application inferences supported by those facts

- For a conventional prompt-submit → streamed text → completion flow, SSE is often the simpler conceptual fit when the browser does not need ongoing client-to-server messages during generation.
- Fetch + SSE parsing is a useful pattern when a generation request needs a POST body, custom authorization headers, or abort control.
- WebSockets are more suitable when the product needs sustained bidirectional interaction, such as frequent in-generation controls, real-time audio, or multiplexed session events.
- A backend proxy is generally useful for protecting provider credentials, enforcing policy, executing tools server-side, and normalizing provider-specific event formats.
- Tool execution should be authorized and validated independently of transport; bidirectionality does not make model-proposed actions safe.

These are design recommendations, not protocol mandates or universal performance claims.

## Suitable scenarios

### Prefer SSE (often via fetch-based streaming) when

- The dominant pattern is one request followed by server-to-browser incremental output.
- The application benefits from typed event-stream conventions for deltas, metadata, and completion events.
- HTTP request semantics, POST bodies, custom headers, or request abort are important; use fetch-based parsing rather than assuming native `EventSource` supports these features.
- The deployment path supports streaming HTTP responses and the team can configure/test buffering and timeouts.

Native `EventSource` is most appropriate when its URL-based request model, credential options, and built-in reconnection behavior fit the application. Its limited request customization should be treated as a design constraint.

### Prefer WebSockets when

- The browser must send frequent controls or other messages while generation is active.
- The product has a sustained interactive session, real-time audio, or multiplexed bidirectional events.
- The hosting path reliably supports WebSocket upgrades and the application can implement message schemas, correlation, authorization, reconnect/resume, and flow control as needed.

### Either can work when

- The main requirement is incremental text display. The choice then depends less on token streaming itself and more on request/authentication needs, interaction direction, infrastructure, and recovery requirements.

## Conclusion and recommendations

There is no categorical winner for browser-based LLM streaming. SSE is a strong default for one-way response delivery, especially when the application can use fetch-based SSE parsing for authenticated POST requests and cancellation. WebSockets are justified when bidirectional interaction is a real product requirement, rather than merely because the response is streamed.

For either choice:
- Define explicit delta, completion, error, and cancellation semantics; do not infer model tokens from transport boundaries or completion from a pause/close.
- Propagate cancellation to upstream generation and distinguish stopping client delivery from stopping model work.
- Test streaming, buffering, idle timeouts, reconnects, and closure through the production network path.
- Implement replay/resume only with explicit application cursors and server-side state; transport reconnection alone is insufficient.
- Keep provider secrets and privileged tool execution server-side where possible, and authorize each operation.
- For WebSockets, plan for receive-side processing limits and application-level flow control; for SSE, verify HTTP streaming flush behavior and native `EventSource` constraints.

## Data gaps and uncertainty

- The findings report that live search results were unavailable during their research runs; cited official/primary-source URLs were not verified against live pages in those runs. Provider-specific details and documentation may have changed.
- No benchmark data is provided to compare latency, throughput, cost, or reliability. Therefore, no claim that either transport is categorically faster or more reliable is supported.
- Proxy buffering, idle timeouts, WebSocket upgrade support, connection duration, and scaling behavior depend on the actual deployment path and must be tested there.
- Browser connection limits and implementation behavior can vary and change; the findings do not support treating any cited limit as universal.
- The findings do not establish a universal receive-side backpressure guarantee for SSE; WebSocket's standard browser API limitation is explicitly noted. Actual buffering and resource behavior should be measured in the target implementation.
- Provider event names, cancellation propagation, replay retention, and tool workflows are application/provider-specific and require verification against current provider documentation and implementation.