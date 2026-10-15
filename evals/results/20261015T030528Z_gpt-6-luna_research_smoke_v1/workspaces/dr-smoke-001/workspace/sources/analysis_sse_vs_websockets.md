# Analysis: SSE vs WebSockets for Browser-Based LLM Assistants

## Data sources

This analysis uses only the three supplied findings files:
- `/workspace/sources/findings_sse_protocol.md`
- `/workspace/sources/findings_websocket_protocol.md`
- `/workspace/sources/findings_llm_streaming.md`

The findings contain fewer than the requested five distinct in-run source URLs. Across the files, the distinct cited URLs are MDN EventSource, an HTML Standard search-result URL whose returned section was not the SSE section, a secondary RFC 6455 listing, MDN WebSocket, and MDN AbortController. The findings themselves note that official primary-source coverage is incomplete: the relevant WHATWG SSE section, official RFC 6455/IETF source, and official LLM-provider streaming documentation were not returned. No URLs have been added or independently verified in this analysis.

## Analysis dimensions

1. Communication direction and interaction pattern.
2. Browser API and request-submission constraints.
3. Stream framing and application message handling.
4. Cancellation, lifecycle, and error handling.
5. Reconnection, resumption, and delivery semantics.
6. Buffering, flow control, and performance uncertainty.
7. Fit for common browser-assistant scenarios.

## Calculation tasks

No numeric calculations are required. The comparison is qualitative and does not make measured performance, latency, or cost claims.

## Comparative analysis

### 1. Directionality and interaction

**Directly evidenced in findings:** SSE/EventSource is described as server-to-client and unidirectional. WebSocket is described as a persistent full-duplex channel in which either endpoint can send independently after connection establishment. The WebSocket protocol evidence is based on a secondary RFC listing rather than an official RFC source; the SSE findings cite MDN for the one-way characterization.

**Engineering inference:** For an assistant that mainly sends generated text and status updates to the browser, SSE aligns with the output direction. Prompts, stop requests, tool inputs, and other client-to-server actions must use a separate request/channel with SSE. WebSocket can carry both generated output and client controls on one persistent channel, but this does not by itself define the application message schema or guarantee delivery to application code.

### 2. Browser API and request submission

**Directly evidenced in findings:** The SSE findings describe native `EventSource` as URL-based and note that its standard constructor does not provide a general custom-header option or request body; the findings explicitly say these API details were not fully corroborated by the retrieved excerpt and should be checked. The LLM-streaming findings state that Fetch supports request bodies and that `AbortController.abort()` can abort a fetch request and response-body consumption. The WebSocket findings establish browser send/receive and connection management, but do not provide a detailed comparison of authentication or request-body behavior.

**Engineering inference:** A browser assistant that submits a prompt as a POST and consumes the response stream can use Fetch streaming when that request shape is needed; cancellation can be wired to an abort signal. If using native EventSource, a design may need to submit the prompt separately and then subscribe to a stream, or use an authentication approach compatible with its API constraints. WebSocket may suit a session-oriented interaction, but the supplied findings do not establish a preferred authentication design or prove that it is simpler overall.

### 3. Framing and application messages

**Directly evidenced in findings:** SSE uses a persistent HTTP response with `text/event-stream`; events are framed as text fields and dispatched at event boundaries. The findings describe `data`, optional named `event` types, and comments as keep-alives, while noting that detailed framing was not independently verified against the relevant WHATWG section. WebSocket uses framed messages after an opening handshake, according to the secondary protocol summary. The LLM-streaming findings emphasize that streamed LLM output is an application-level sequence: clients must parse provider framing and distinguish content, completion, and errors; provider-specific formats were not verified.

**Engineering inference:** SSE provides a defined event-stream convention that can represent token/content updates and lifecycle events, while WebSocket applications need to define and parse their own message envelope for content, completion, errors, and controls. Neither transport removes the need to handle provider-specific event semantics or application lifecycle states.

### 4. Cancellation, lifecycle, and errors

**Directly evidenced in findings:** Fetch abort can stop request and response-body consumption. The SSE findings say `EventSource.close()` terminates its connection. The WebSocket findings describe connection management and message send/receive, but the supplied evidence does not detail a particular cancellation protocol. The LLM findings state that clients should handle response status, stream-level completion/errors where defined, network interruption, and user cancellation; provider retry and error schemas are not established.

**Engineering inference:** With Fetch-based HTTP streaming, a stop action can abort the active fetch, while the application should distinguish user cancellation from provider failure. With SSE, closing the event source ends the browser-side connection, but whether generation itself stops depends on server/application behavior. With WebSocket, a stop message can be sent over the bidirectional channel, but the server must implement and acknowledge that control semantics. In all cases, transport termination and model-generation termination should not be assumed equivalent without application-level behavior.

### 5. Reconnection, resumption, and delivery

**Directly evidenced in findings:** The SSE findings describe EventSource reconnection and `id`/`Last-Event-ID` cursor behavior, but explicitly state that the relevant standard section was not returned and that a cursor is not a replay guarantee. Server-side retention/replay and deduplication are needed for robust resumption. The WebSocket findings do not establish automatic reconnection or replay semantics.

**Engineering inference:** If an assistant must resume an interrupted answer, SSE's described event-ID mechanism can provide a cursor foundation only when the server implements replay and the client handles duplicates/gaps. A WebSocket implementation would likewise need application-defined reconnect, session recovery, and replay behavior; the supplied findings do not support a claim that either transport guarantees seamless recovery.

### 6. Buffering, flow control, and performance

**Directly evidenced in findings:** MDN WebSocket documentation is reported to warn that the browser WebSocket API has no receive-side backpressure mechanism; messages arriving faster than processing can consume memory or make the page unresponsive. The SSE findings mention possible framing/event-dispatch overhead for token-level events and batching as a design trade-off, but identify this as protocol-level engineering inference rather than LLM-specific evidence. The findings provide no comparative benchmarks or measured latency/throughput results.

**Engineering inference:** WebSocket clients should bound application queues and consider coalescing UI updates if incoming messages outpace rendering. SSE clients also need sensible parsing and rendering behavior, but the supplied evidence does not establish a directly comparable backpressure guarantee for EventSource. Batching may reduce per-event overhead but can increase perceived delay; the appropriate balance depends on workload and must be measured. No conclusion that one transport is inherently faster, cheaper, or more scalable is supported here.

## Suitable scenarios

- **SSE / HTTP streaming is a reasonable fit** when the dominant pattern is server-to-browser generated output, client controls can be separate HTTP requests, and the application benefits from event-stream framing. Fetch streaming is particularly relevant when the prompt must be submitted in a request body and browser abort-based cancellation is desired; this is distinct from using native EventSource.
- **WebSocket is a reasonable fit** when the assistant needs frequent two-way interaction over a persistent channel—for example, output streaming alongside client control or interaction messages—and the application is prepared to define message schemas, lifecycle behavior, and queue limits.
- **Either can fit** a basic token-streaming assistant. The choice depends on interaction direction, request/authentication constraints, recovery requirements, and implementation needs—not on performance claims absent from these findings.

## Analysis conclusions and recommendations

1. Choose SSE or HTTP response streaming when output delivery is predominantly one-way and client-to-server actions can remain separate. Decide explicitly whether the browser will use native EventSource or Fetch streaming; their request and cancellation characteristics should not be conflated.
2. Choose WebSocket when bidirectional messaging is a core requirement rather than merely a convenience. Define application-level message types for content, completion, errors, cancellation, and controls, and bound incoming work to mitigate the documented lack of browser receive-side backpressure.
3. For either option, specify cancellation semantics, terminal/error events, reconnect behavior, and whether interrupted generations can be resumed. Do not treat connection reconnection or a cursor as proof of replay or exactly-once delivery.
4. Benchmark under the actual browser, network, proxy, and rendering conditions before making latency, throughput, or resource-efficiency decisions; the supplied findings contain no comparative measurements.

## Data gaps and uncertainty

- The findings contain fewer than the requested five distinct in-run source URLs, and official primary-source coverage is incomplete. In particular, the relevant WHATWG SSE section and official RFC 6455/IETF source were not returned; the WebSocket protocol summary relies on a secondary listing.
- The SSE findings flag detailed framing, reconnection/ID behavior, and EventSource constructor constraints as incompletely corroborated by retrieved excerpts.
- No official OpenAI or Anthropic streaming documentation was returned. Provider event names, exact wire formats, retry behavior, and error schemas remain unverified.
- No comparative performance, latency, throughput, scalability, or cost data is present. Any performance preference would require additional evidence or testing.
- The scenario recommendations above are engineering inferences from the supplied protocol/API findings, not direct claims from LLM-specific comparative studies.
