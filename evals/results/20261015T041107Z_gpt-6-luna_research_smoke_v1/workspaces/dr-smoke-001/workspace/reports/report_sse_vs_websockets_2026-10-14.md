# SSE vs. WebSockets for Streaming LLM Responses in Browser-Based AI Assistants

## Background

**Executive summary:** SSE/HTTP is generally a strong fit for one-way generated output, while WebSockets are appropriate when the interaction is genuinely bidirectional. Native `EventSource` has request constraints; Fetch response streaming is a possible HTTP alternative when custom request controls are needed. Neither transport defines LLM application semantics, and the reviewed evidence does not establish a universal latency or throughput winner.

Browser-based AI assistants commonly need to show generated output before the full response is complete. The transport must support incremental delivery while the application handles lifecycle events, errors, and user interaction. The relevant choice is not simply “which is faster”: SSE and WebSockets differ in directionality, browser APIs, framing, reconnection behavior, and the amount of application protocol the team must define.

The cited OpenAI streaming guide documents HTTP streaming over SSE for `stream=true`, with typed events such as `response.created`, `response.output_text.delta`, `response.completed`, and `error`. It also points to WebSocket mode for persistent transport and incremental inputs. These are documented implementation patterns, not proof that one transport is universally superior.

## Key Findings

### SSE / HTTP response streaming

SSE is a one-way server-to-client event mechanism over an HTTP response. Its UTF-8 `text/event-stream` format uses line-oriented fields such as `data:`, `event:`, `id:`, and `retry:`, with a blank line delimiting each event. Native `EventSource` dispatches complete events, supports reconnection, and can send a `Last-Event-ID` cursor after receiving an event ID. These conventions do not guarantee that the server replays events or that delivery is exactly once.

The native `EventSource` constructor accepts a URL and an optional credentials setting, but does not expose arbitrary headers, a request method, or a body. This can be inconvenient for APIs that require a POST prompt payload or custom authorization headers. A browser can instead use Fetch and consume `Response.body` as a `ReadableStream`; the stream yields byte chunks, so the client must decode and parse application framing across arbitrary chunk boundaries. The MDN reference directly documents the readable response body and reader-based consumption; using Fetch for custom request controls and parsing application framing are implementation implications, not claims made by that page.

### WebSockets

WebSockets provide a persistent, bidirectional channel. The browser API delivers complete messages to JavaScript; protocol frame fragmentation does not itself expose partial frames as incremental script events. Applications can send successive messages for incremental output, but must define message types and semantics.

The browser API supports text and binary payloads and exposes connection lifecycle states. It also exposes `bufferedAmount` for queued outbound application bytes, but this is not a measure of server processing or inbound backlog. Reconnection, replay, request IDs, cancellation, and delivery guarantees are application responsibilities.

### LLM-specific considerations

Typed streaming events support a UI state model: initialize a response, append text deltas, handle errors, and finalize on completion. Streaming also creates a moderation-timing trade-off: the cited guide warns that partial completions are harder to moderate and that moderation scores arrive only after the full output is available. This concern applies to incremental display generally and does not establish a transport-specific advantage.

## Evidence and Analysis

The evidence base includes five distinct pages verified during this run: the WHATWG HTML Standard, WHATWG WebSockets Standard, RFC 6455, OpenAI streaming guide, and MDN `Response.body` reference. The MDN page directly documents `Response.body` as a `ReadableStream` and demonstrates reading it with a reader. The further suggestion to use Fetch for POST bodies or custom headers follows from the Fetch request model and is an implementation inference; the MDN page itself does not document those request options. Parsing application framing across arbitrary byte chunks is an engineering requirement for stream consumers, not an LLM-specific rule stated by that page.

| Dimension | SSE / HTTP | WebSockets |
|---|---|---|
| Direction | Server-to-client stream; client input is separate. | Bidirectional messages over a persistent connection. |
| Browser delivery | EventSource dispatches complete, blank-line-delimited text events. | JavaScript receives complete messages, not individual frames. |
| Application structure | Standard text event fields and event-ID/retry conventions. | Application defines message schema, chunk boundaries, and semantics. |
| Reconnection | EventSource reconnects and can send `Last-Event-ID`; replay is not guaranteed by the protocol. | Reconnect/resume policy must be implemented by the application. |
| Request constraints | Native EventSource lacks arbitrary headers, method, and body; Fetch streaming is an alternative for custom HTTP requests. | Persistent bidirectional API, but explicit lifecycle and application protocol handling are needed. |
| Flow control evidence | No direct comparative backpressure evidence in the reviewed sources. | `bufferedAmount` reports queued outbound bytes; it is not a general end-to-end flow-control signal. |

**Trade-off:** SSE offers a standard event-oriented model that maps naturally to one-way generated output. WebSockets offer bidirectionality and payload flexibility, at the cost of more application-defined protocol and lifecycle behavior. Both can deliver incremental updates, but the application must choose useful event/message boundaries. Neither should be selected based on assumed performance superiority: the reviewed sources provide no comparative latency, throughput, or scalability measurements.

## Recommendations

1. **Choose SSE/HTTP for the default request-then-response assistant flow** when the browser mainly submits a prompt and renders incremental server output. Use typed events for deltas, completion, and errors; flush complete event records promptly.
2. **Use Fetch response streaming when native EventSource’s request interface is too restrictive**, such as when the API requires a POST body or custom headers. Parse the stream incrementally and handle arbitrary byte/event boundaries; do not assume each network chunk equals one event or token. This is an implementation recommendation based on the Fetch streaming capability and request model, not a transport guarantee.
3. **Choose WebSockets when bidirectionality is a product requirement**, such as incremental input updates, persistent interactive sessions, or ongoing control messages on the same connection. Define message schemas, request/generation IDs, cancellation, reconnect/resume behavior, and resource limits explicitly.
4. **For either transport, specify application semantics.** Decide how completion and errors are represented, whether reconnect restarts or resumes, how duplicate/missing events are handled, and how partial output is moderated before display.
5. **Benchmark the actual deployment if performance is decisive.** The reviewed standards and vendor guide do not establish a universal latency, throughput, or infrastructure-efficiency winner.

## Limitations

The evidence is primarily technical standards and vendor documentation, supplemented by an MDN browser API reference. It does not include controlled benchmarks, quantified browser or proxy behavior, or deployment-specific operational data. The standards do not define LLM token boundaries, replay storage, exactly-once delivery, or application cancellation semantics. The Fetch `Response.body` reference documents a readable response stream but does not itself prescribe LLM framing or request customization. Recommendations about UI state handling, moderation workflow, and transport fit are engineering inferences from the documented capabilities.

## References

### Primary standards and technical documentation

1. [HTML Standard — Server-sent events](https://html.spec.whatwg.org/multipage/server-sent-events.html)
2. [WebSockets Standard](https://websockets.spec.whatwg.org/)
3. [RFC 6455: The WebSocket Protocol](https://www.rfc-editor.org/info/rfc6455/)
4. [Streaming API responses | OpenAI API](https://developers.openai.com/api/docs/guides/streaming-responses.md)
5. [Response: body property — Web APIs | MDN](https://developer.mozilla.org/en-US/docs/Web/API/Response/body)

The MDN page is a browser API reference; the other listed sources are standards or vendor technical documentation. No performance benchmark source was identified in this research.