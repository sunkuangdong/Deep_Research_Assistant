# SSE vs WebSockets for Streaming LLM Responses in Browser-Based AI Assistants

## Background

Browser-based AI assistants commonly stream generated output incrementally so users can see a response before generation is complete. The transport choice affects how the browser receives updates, how client actions such as prompt submission and cancellation are sent, and how the application handles interruption and recovery. Server-Sent Events (SSE) and WebSockets can both support streaming, but they expose different communication patterns and browser APIs.

A key distinction is that “SSE” may refer to the event-stream format and HTTP response pattern, or specifically to the browser's native `EventSource` API. Fetch-based HTTP response streaming is another option and should not be conflated with native EventSource: Fetch supports request bodies and can be aborted with `AbortController`, while EventSource is designed to consume an event stream.

## Key Findings

- **SSE is naturally aligned with one-way output.** Native EventSource receives server-to-browser events over a persistent HTTP response. Client actions such as submitting prompts, sending tool inputs, or stopping generation require a separate request or channel.
- **WebSockets provide a persistent bidirectional channel.** Either endpoint can send messages after connection establishment, which can consolidate output and client controls. The application must define message types and lifecycle semantics.
- **Request shape and cancellation matter.** Fetch streaming supports a POST body and `AbortController` cancellation. Native EventSource has a narrower URL-based interface; the findings flag its request-header/body constraints as incompletely corroborated in the retrieved excerpts. WebSocket can carry client messages, but the application must implement what those messages mean.
- **Recovery is an application responsibility.** SSE event IDs can serve as a resume cursor when supported, but do not guarantee replay or exactly-once delivery. WebSocket recovery likewise requires application-defined reconnect and replay behavior.
- **Browser WebSocket receive-side backpressure is a concern.** MDN warns that the browser WebSocket API has no way to apply backpressure; an application should bound queues and avoid letting incoming messages overwhelm rendering or processing.
- **No evidence here establishes that one transport is inherently faster or cheaper.** The findings contain no comparative benchmarks, and provider-specific LLM event formats were not verified.

## Evidence and Analysis

### Communication pattern and framing

SSE uses an HTTP event stream with `text/event-stream` framing and is unidirectional from server to client. This is a good conceptual match for generated text and status updates. WebSockets use a persistent full-duplex connection, allowing the browser to send controls while receiving output. That flexibility is useful only when the application needs it; it also means the application must define and parse its own message envelope for content, completion, errors, and controls.

For a simple assistant, a common architecture is to submit a prompt over HTTP and stream the response back. If the prompt must be sent in a POST body, Fetch streaming may be a better fit than native EventSource. If the assistant is session-oriented and needs frequent two-way messages, WebSocket may simplify the channel topology, though not necessarily the overall implementation.

### Cancellation, errors, and recovery

Fetch can be aborted through `AbortController`, which stops the request and response-body consumption. Closing an EventSource ends the browser-side connection; whether that also stops model generation depends on server-side behavior. A WebSocket can carry a stop message, but the server must implement and acknowledge cancellation semantics. In all cases, transport termination should not be assumed to equal model-generation termination.

EventSource reconnection and event IDs can support a cursor-based resume design, but the server must retain or reconstruct events and implement replay. A cursor alone does not guarantee no gaps, duplicates, or exactly-once delivery. WebSocket applications also need explicit reconnect, session recovery, and replay logic. Both designs should define terminal events, error handling, and what happens when a connection is interrupted.

### Buffering and performance

The browser WebSocket API's lack of receive-side backpressure is a documented risk when messages arrive faster than the application can process them. Bound queues, coalesce UI updates where appropriate, and define overload behavior. The available evidence does not establish a directly comparable EventSource backpressure guarantee. Nor does it provide measured latency, throughput, scalability, or cost comparisons. Any claim that one transport is faster or more efficient should be validated under the actual browser, network, proxy, and rendering conditions.

### Evidence quality

The findings preserve five distinct URLs, but primary-source coverage is incomplete. MDN documentation supports browser API behavior; the WebSocket protocol summary came from a secondary listing rather than the official RFC page. The returned WHATWG result was not the relevant SSE section, and official LLM-provider streaming documentation was not retrieved. Accordingly, detailed protocol edge cases and provider-specific event formats remain uncertain.

## Recommendations

1. **Prefer SSE or HTTP response streaming for predominantly one-way generation.** Use it when the browser mainly receives generated text/status and client controls can be separate HTTP requests. Choose native EventSource when its request model fits; choose Fetch streaming when the prompt needs a request body or abort-based cancellation is important.
2. **Prefer WebSockets when bidirectional messaging is a core requirement.** Examples include frequent client controls or interactive messages sharing a persistent session with streamed output. Define message schemas, cancellation acknowledgments, terminal/error states, reconnect behavior, and bounded client queues.
3. **Treat recovery and cancellation as application features, not transport guarantees.** Specify whether interrupted generations can resume, how replay and deduplication work, and whether a user stop request actually halts server-side generation.
4. **Benchmark before making performance-based choices.** Test representative browsers, network conditions, proxies, message rates, and rendering workloads; the available evidence does not support a universal performance winner.

## Limitations

This assessment is based on a limited set of retrieved documentation. The relevant WHATWG SSE section and official RFC 6455/IETF page were not returned in the search results; the WebSocket protocol summary is secondary. Official OpenAI or Anthropic streaming documentation was also not retrieved, so provider-specific event names, error schemas, and retry behavior are not established. Some EventSource API constraints and SSE reconnection details are flagged in the findings as incompletely corroborated. No comparative performance measurements were found. Recommendations are therefore architectural guidance based on documented browser API characteristics and should be validated against the chosen provider and deployment environment.

## References

### Browser and protocol documentation

- [MDN: EventSource](https://developer.mozilla.org/en-US/docs/Server-sent_events/EventSource)
- [WHATWG HTML Standard search result (returned section is not the SSE section)](https://html.spec.whatwg.org/multipage/iana.html)
- [MDN: WebSocket](https://developer.mozilla.org/en-US/docs/Web/API/WebSocket)
- [RFC 6455 listing and summary (secondary source)](https://www.antpedia.com/standard/2001864819.html)
- [MDN: AbortController.abort()](https://developer.mozilla.org/en-US/docs/Web/API/AbortController/abort)

The WHATWG result above is not the relevant SSE section, and the RFC 6455 link is a secondary listing; neither should be treated as a verified official primary-source page.