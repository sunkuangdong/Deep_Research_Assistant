# Findings: WebSockets for Browser-Based LLM Response Streaming

## Research scope
This note covers WebSockets as a browser-to-service transport for streaming LLM responses: protocol directionality, browser API, opening handshake and origin/security considerations, message framing, reconnect semantics, flow control/backpressure, and operational tradeoffs. It distinguishes protocol/API guarantees from deployment-dependent behavior. It is not a recommendation that WebSockets are always preferable to HTTP streaming.

## Key findings

- **Full-duplex transport:** After a successful opening handshake, WebSocket provides a two-way channel over a single underlying TCP connection; either endpoint can send messages independently. This supports simultaneous client-to-server actions (for example, cancellation or interaction) and server-to-browser token/event delivery. It is a transport, not an LLM token protocol: applications must define event types, ordering/IDs, completion and error signaling, and serialization. The RFC describes the protocol as two-way communication and a handshake followed by framed data over TCP.  
  Source: [RFC 6455 overview (search result)](https://websocket.xiniushu.com/)

- **Browser API:** The browser `WebSocket` object creates/manages a connection and sends/receives data. MDN describes it as widely available across browsers since July 2015. The standard API exposes message events and `send()`, but does not itself provide LLM-specific streaming semantics; applications commonly deliver incremental text or structured events as messages.  
  Source: [MDN WebSocket API](https://developer.mozilla.org/en-US/docs/Web/API/WebSocket)

- **Handshake and origin/security:** RFC 6455’s security model is based on browser origins, and the opening handshake precedes WebSocket data transfer. For browser deployments, the server should validate the `Origin` against an explicit allowlist where appropriate; origin checking is not a substitute for authentication or authorization. Use `wss://` to protect traffic in transit, authenticate the connection, authorize requested model/session actions, and avoid treating a successful upgrade as proof of user permission. The search results returned a secondary RFC overview rather than the RFC Editor primary text, so exact normative handshake requirements were not independently verified from an official RFC URL in this run.  
  Source: [RFC 6455 overview (search result)](https://websocket.xiniushu.com/)

- **Framing:** WebSocket carries framed messages, with text and binary data and protocol control frames; application messages may be fragmented at the protocol layer. For LLM streaming, implementations can send successive application messages (often simpler for incremental events) or use a message representation that the client parses incrementally. Do not assume one WebSocket message equals one model token, or that TCP packet boundaries correspond to application message boundaries. The available search results did not expose the official RFC text, so detailed frame-level normative requirements are not asserted here.  
  Source: [RFC 6455 overview (search result)](https://websocket.xiniushu.com/)

- **Reconnect behavior:** A WebSocket connection is a live connection, not a durable stream with automatic replay. Browser/API documentation in the returned results does not promise automatic reconnection or recovery of missed messages. Applications should implement reconnect policy (bounded retries/backoff, jitter, authentication refresh as needed) and define resume/replay semantics using request IDs, sequence numbers or cursors if generation continuity matters. Whether a generation can be resumed depends on server and model-serving architecture.

- **Flow control and backpressure:** MDN explicitly states that the browser `WebSocket` API has no way to apply backpressure. If messages arrive faster than the application processes them, buffering can consume device memory or make the page unresponsive. For LLM output, bound queues and message sizes, process incrementally, and consider application-level pacing/credits or cancellation. These measures are application design choices, not guarantees supplied by the browser API. MDN points to `WebSocketStream` as an alternative with automatic backpressure, but its availability/production suitability should be checked for target browsers rather than assumed.  
  Source: [MDN WebSocket API](https://developer.mozilla.org/en-US/docs/Web/API/WebSocket)

- **Operational implications (deployment-dependent):** A long-lived connection can reduce repeated request setup and enables bidirectional control, but requires infrastructure to support persistent upgraded connections, connection lifecycle management, capacity planning, and observability. Proxies/load balancers, idle timeouts, network changes, and server restarts may terminate connections; exact behavior depends on the deployment. Heartbeats, timeout policy, graceful close, reconnect, and replay/resume are therefore operational design concerns, not universal protocol guarantees. WebSocket also does not inherently provide application-level delivery acknowledgments or exactly-once processing; define idempotency and duplicate handling if reconnect/retry can repeat actions.

## Evidence and uncertainty
The strongest directly returned primary documentation is MDN’s browser API page, which explicitly documents the API and lack of backpressure. Search results did not return an official RFC Editor URL despite a domain-qualified query; the RFC-related result available was a secondary overview. Accordingly, RFC-level details above are limited to high-level claims visible in that result, and no unreturned RFC URL is cited. Reconnect, infrastructure behavior, and recommended application patterns are deployment-dependent engineering implications, not normative protocol requirements. The search evidence is insufficient to make browser-by-browser claims about `WebSocketStream` support or specific proxy timeout behavior.

## References
- [RFC 6455 overview (secondary result)](https://websocket.xiniushu.com/)
- [MDN WebSocket API](https://developer.mozilla.org/en-US/docs/Web/API/WebSocket)
