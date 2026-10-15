# Analysis: SSE vs. WebSockets for Browser-Based LLM Streaming

## Data sources

- `/workspace/sources/findings_sse_protocol.md`
- `/workspace/sources/findings_websocket_protocol.md`
- `/workspace/sources/findings_llm_streaming.md`
- Supplemental evidence supplied in the task: MDN `Response.body` page at `https://developer.mozilla.org/en-US/docs/Web/API/Response/body`. This URL is treated only as user-provided evidence available in the run; no additional URL or claim from it is introduced here.

The comparison below distinguishes documented facts in the findings from engineering inferences drawn from them.

## Comparison dimensions

| Dimension | SSE / HTTP response stream | WebSockets | Evidence status and implications |
|---|---|---|---|
| Communication direction | One-way server-to-client event stream. Client input is sent separately. | Persistent, bidirectional channel; either endpoint can send independently. | **Documented.** SSE naturally fits a request followed by generated output; WebSockets can carry ongoing client input and server output on one connection. |
| Browser consumption model | Native `EventSource` parses UTF-8 `text/event-stream` records, dispatching events after a blank-line delimiter. The supplied MDN page concerns `Response.body`; the findings do not establish its detailed behavior or how it is used in a particular implementation. | Browser scripts receive complete WebSocket messages, not individual protocol frames. Separate application messages can represent incremental updates. | **Documented** for EventSource and WebSocket message delivery. **Inference:** choose event/message boundaries to match UI update units. Do not assume WebSocket frame fragmentation exposes partial content to JavaScript. |
| Payload and event structure | Text-based, line-oriented fields such as `data`, `event`, `id`, and `retry`; named events and JSON-in-data are possible. | Text and binary messages are supported; application protocol defines message meaning and chunking. | **Documented.** SSE is a direct fit for textual deltas and typed lifecycle events; WebSockets offer payload flexibility, but LLM semantics still need an application schema. |
| Client request customization | Native `EventSource` constructor exposes URL and optional credentials setting, but not arbitrary headers, method, or body. | Browser WebSocket API establishes a connection through its constructor and supports named subprotocol negotiation; it is not raw socket access. | **Documented.** Native EventSource can be awkward where an API requires a POST body or arbitrary authorization headers. The findings do not establish that WebSockets automatically solve every authentication or deployment constraint. |
| Reconnection and resumption | EventSource reconnects after recoverable closure; `retry` can influence delay and `id` can be sent back as `Last-Event-ID`. This is a cursor mechanism, not a guarantee of replay or exactly-once delivery. | Application must handle lifecycle and implement reconnect/resume behavior if needed; protocol does not define LLM replay semantics. | **Documented.** SSE has a built-in reconnect mechanism, but reliable continuation still requires server-side retention/replay and application semantics. WebSocket continuity likewise requires application design. |
| Backpressure and buffering | Findings describe event parsing but do not establish a general backpressure comparison. | `bufferedAmount` reports queued outbound application bytes; browser API does not provide a `ReadableStream`-style per-chunk receive interface or send-completion promise. | **Documented** for WebSockets; **insufficient evidence** for a direct comparative performance claim. Engineering should not interpret `bufferedAmount` as server processing or inbound backlog. |
| Lifecycle and operational model | Long-lived HTTP response; event framing and prompt flushing of complete records matter for timely dispatch. | Explicit `CONNECTING`, `OPEN`, `CLOSING`, `CLOSED` lifecycle; connection duration, concurrency, and resource limits matter. | **Documented** in findings. **Inference:** operational monitoring and failure handling should be designed for either transport; the specific burden differs by API and deployment. |
| LLM-specific event semantics | The cited streaming guide documents HTTP/SSE events including `response.created`, `response.output_text.delta`, `response.completed`, and `error`. | WebSocket transports messages but does not define token boundaries, completion, errors, cancellation, or request IDs. The guide positions WebSocket mode for persistent transport and incremental inputs. | **Documented.** A typed event/state model is useful regardless of transport; WebSocket requires the application protocol to define it. |
| Moderation timing | Streaming partial output is harder to moderate; moderation scores described in the guide arrive after full output, not with partial deltas. | Same product-level issue applies if partial output is revealed incrementally; the findings do not establish a transport-specific moderation advantage. | First sentence **documented** for streaming generally. Applying it to either transport is an **engineering inference**; no comparative moderation evidence is provided. |

## Key trade-offs

1. **Simplicity of one-way output vs. bidirectional interaction.** SSE has a narrow, event-oriented model suited to server-pushed text and lifecycle events. WebSockets support upstream and downstream messages on one persistent connection, which can be useful for incremental inputs, control messages, or interactive sessions. These are capability differences, not evidence that one has universally lower latency or higher throughput.
2. **Built-in event-stream conventions vs. application-defined messaging.** SSE provides a standard text event format and EventSource reconnection/ID conventions. WebSockets provide message transport and text/binary support, while the application defines message types, chunk boundaries, replay, and acknowledgements as needed.
3. **Native EventSource constraints vs. WebSocket lifecycle work.** EventSource does not expose arbitrary request headers or a request body. WebSockets avoid the one-way-only limitation but require explicit connection-state handling and application-level reconnect/resume decisions. The findings do not support a blanket claim that WebSockets are simpler for authentication or more reliable.
4. **Incremental delivery is not the same as transport framing.** SSE dispatches complete event records; WebSocket JavaScript receives complete messages rather than individual frames. In both cases, the server/application must choose boundaries that allow the UI to render useful deltas promptly.
5. **Streaming creates product-level moderation considerations.** Revealing partial output can precede availability of full-output moderation scores. This is a streaming UX and safety trade-off, not a demonstrated reason to select one transport over the other.

## Suitable scenarios

### SSE is a suitable candidate when

- The interaction is primarily a request followed by incremental server-to-browser output.
- Text deltas and typed lifecycle/error events are sufficient, and the application can use an HTTP/SSE stream.
- Native EventSource’s request limitations are compatible with the API design, or another supported request/streaming mechanism is deliberately chosen.
- Reconnection is useful and the application can define event IDs plus server-side replay behavior where continuity is required.

The LLM streaming findings document HTTP/SSE as the guide’s pattern for `stream=true`; this supports SSE as a directly documented option for ordinary incremental response output, not as a universal preference.

### WebSockets are a suitable candidate when

- The assistant interaction needs persistent, bidirectional communication, such as incremental input updates or ongoing client control messages alongside generated output.
- The application benefits from text/binary messages or a negotiated subprotocol and is prepared to define message schemas and lifecycle semantics.
- The team can implement and operate connection-state handling, reconnect/resume policy, and any required application-level flow control.

The LLM streaming findings identify WebSocket mode as an option for persistent transport and incremental inputs; they do not claim that ordinary text streaming requires WebSockets.

## Calculation tasks

No calculations were requested or needed. No numerical comparison is made.

## Analysis conclusions

For a browser assistant whose main requirement is to display a generated answer progressively after a request, SSE/HTTP is a strong fit in the documented patterns: it is one-way, text-oriented, event-structured, and the LLM guide explicitly uses it for streaming responses. WebSockets are more compelling when the product needs ongoing bidirectional interaction or incremental inputs over a persistent connection. Neither transport supplies complete LLM semantics such as token meaning, cancellation, replay guarantees, or exactly-once delivery; those remain application responsibilities. Selection should therefore follow interaction requirements and API constraints rather than assumed performance superiority.

## Data gaps and uncertainty

- The findings provide no measured latency, throughput, resource consumption, or comparative scalability data; no performance winner can be inferred.
- The supplied MDN `Response.body` page is acknowledged as supplemental evidence, but its contents are not represented in the findings provided here. This analysis therefore makes no specific claim about `Response.body` behavior or its comparative role.
- The findings do not compare browser support, proxy/load-balancer behavior, deployment configuration, or operational limits quantitatively.
- SSE reconnection does not itself guarantee replay or exactly-once delivery; WebSocket resumption and delivery semantics are also application-defined.
- Authentication, cancellation, and request-body requirements depend on the specific API and implementation. The findings establish native EventSource’s interface constraints but do not establish a universal WebSocket solution to them.
- Moderation timing is documented for streaming in the LLM guide, but no transport-by-transport moderation comparison is available.
