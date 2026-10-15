## Background

Browser-based AI assistants need to deliver generated text incrementally while handling user actions such as cancellation, retries, and follow-up input. Server-Sent Events (SSE) and WebSockets can both carry streamed output, but they expose different interaction models. SSE is an HTTP event stream designed for server-to-client events; WebSockets provide a bidirectional channel. The choice should follow the product’s communication pattern and operational constraints, not an assumed universal performance advantage.

This report compares native browser `EventSource` with the browser WebSocket API and distinguishes native SSE from fetch-based SSE, which can provide a more flexible HTTP request shape while requiring client-side stream parsing.

## Key Findings

- **SSE is a natural fit for one-way generated output.** Its `text/event-stream` format provides event framing, and native `EventSource` includes reconnection conventions and `Last-Event-ID` support. Durable replay still requires server-side event retention and replay logic.
- **Native `EventSource` has a constrained request interface.** It uses GET and does not expose a request body or arbitrary headers. For POST prompts, bearer authorization headers, or more control over cancellation and retry, fetch-based SSE is an option, with additional client parsing and lifecycle work.
- **WebSockets fit ongoing bidirectional interaction.** They allow client and server messages over one connection, but the application must define its message protocol and implement reconnect/resume behavior. The browser WebSocket API does not provide backpressure.
- **Neither transport guarantees reliable generation resumption or exactly-once delivery.** Those properties require application and server design.
- **Deployment behavior matters.** SSE may be affected by intermediary buffering and idle timeouts; WebSockets require infrastructure that supports persistent upgraded connections. These are deployment-dependent considerations, not universal guarantees. Validate either option through the actual browser, proxy, load balancer, and hosting path.

## Evidence and Analysis

### Interaction model and implementation

The W3C Server-Sent Events Recommendation describes a UTF-8 line-framed `text/event-stream` with `data`, `event`, `id`, and `retry` fields; a blank line dispatches an event. This maps cleanly to incremental server-to-browser output. Native `EventSource` handles the event format and reconnect conventions, but its GET-only request interface can be limiting for assistants that submit prompts via POST or require custom authorization headers. Fetch-based SSE can retain the event-stream format while allowing a more flexible request, but the client must read and parse the stream.

WebSockets provide a two-way channel after the opening handshake. This is useful when client actions and generated output need to interleave over one connection. However, WebSockets are a transport rather than an LLM event protocol: the application must define message types, ordering, completion and error signaling, and any replay semantics. MDN documents that the browser WebSocket API lacks backpressure, so applications should bound queues and process messages incrementally.

### Reliability and operations

Native EventSource reconnects and can send `Last-Event-ID` after receiving event IDs. This is a useful convention, not a guarantee that a generation can resume: the server must retain and replay the relevant events. WebSockets do not provide automatic reconnection or missed-message recovery in the cited browser API evidence; applications need explicit retry and, if required, cursor or sequence-number logic.

Both transports need operational testing. The research findings identify SSE intermediary buffering and idle timeouts as deployment-dependent risks, for which heartbeats may help in some configurations. WebSocket deployments need infrastructure that supports upgraded, persistent connections and careful lifecycle management. The available evidence does not establish that either transport is universally cheaper, faster, or easier to scale.

### Security and request handling

Native EventSource supports browser-managed credentials through its credentials option, subject to CORS configuration, but cannot attach arbitrary headers. Avoid placing secrets in stream URLs. For WebSockets, the findings recommend `wss://`, authentication and authorization, and validating browser origins where appropriate; origin validation is not a substitute for authorization. These are security design recommendations. The WebSocket findings did not retrieve the official RFC Editor page, so detailed normative handshake claims are not made here.

### Comparative assessment

| Dimension | SSE | WebSockets |
|---|---|---|
| Primary interaction | Server-to-browser event stream | Bidirectional messages |
| Native browser request | GET; no body or arbitrary headers | Persistent connection; application-defined messages |
| Reconnect/resume | Native reconnect and event-ID convention; replay is server-dependent | Application-defined reconnect and replay |
| Flow control | No comparative guarantee established by this evidence | Browser API has no backpressure |
| Operational focus | HTTP streaming, buffering, idle timeouts, CORS | Upgrade support, persistent connection lifecycle, reconnect |
| Best fit | Predominantly one-way output | Frequent two-way interaction on one connection |

The comparison is qualitative. No comparative latency, throughput, cost, or production-scale measurements were found in the evidence reviewed.

## Recommendations

1. **Choose SSE as the default for straightforward, predominantly one-way LLM output** when a GET stream and the native EventSource credential model fit. Use event IDs only if the backend can replay from a cursor; otherwise treat reconnect as a new or potentially incomplete stream.
2. **Choose fetch-based SSE when the event-stream model fits but native EventSource does not.** This is appropriate when prompt submission needs POST, custom headers, or more explicit cancellation and retry control. Account for client-side parsing and stream lifecycle handling.
3. **Choose WebSockets when bidirectional interaction is a core product requirement**, such as frequent client control messages interleaved with generated output. Budget for an application protocol, authentication/authorization, reconnect and replay semantics, bounded client queues, and infrastructure support for persistent upgraded connections.
4. **Test the real deployment path before committing.** Verify streaming visibility, buffering, idle timeouts, reconnect behavior, cancellation, and authentication through the target browsers and intermediaries. Do not select a transport based solely on presumed speed or scalability.

## Limitations

The evidence reviewed includes a W3C SSE Recommendation and MDN browser API references. The EventSource MDN result was a Spanish-language page. The WebSocket RFC-related search result was a secondary overview rather than the official RFC Editor text; detailed RFC-level claims are therefore limited. No provider-specific LLM API documentation or deployment measurements were collected, and no comparative benchmarks were available. Proxy behavior, browser behavior, and infrastructure limits can vary by environment. Recommendations about scenario fit are engineering inferences from the documented APIs, not measured performance conclusions.

## References

- [Server-Sent Events — W3C Recommendation](https://www.w3.org/TR/2015/REC-eventsource-20150203/)
- [EventSource — MDN Web Docs (Spanish)](https://developer.mozilla.org/es/docs/Web/API/EventSource)
- [WebSocket API — MDN Web Docs](https://developer.mozilla.org/en-US/docs/Web/API/WebSocket)
- [RFC 6455 overview (secondary source)](https://websocket.xiniushu.com/)

**Source-count limitation:** Only four distinct source URLs were returned and recorded in the research findings. The requested minimum of five distinct links could not be met without an additional verified search result; no fifth URL is invented. The RFC overview is secondary, not an official RFC source.
