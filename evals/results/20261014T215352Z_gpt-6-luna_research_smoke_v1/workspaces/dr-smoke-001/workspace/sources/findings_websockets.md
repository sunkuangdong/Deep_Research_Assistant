# Findings: WebSockets for Streaming LLM Responses
## Research scope
This note covers only WebSocket protocol and browser behavior relevant to streaming LLM responses: bidirectional communication, browser API and lifecycle, framing, backpressure limitations, and operational considerations supported by primary documentation. It does not assess application architectures or compare transport alternatives.

## Key findings
- WebSocket provides a persistent, full-duplex communication channel over a single TCP connection after an opening handshake. Either endpoint can send data independently; this supports server-pushed response chunks while the browser can send messages on the same connection. The protocol itself does not define LLM token semantics or guarantee that each application-level chunk maps to one protocol frame.
  Source: [RFC 6455, sections 1.2 and 5](https://www.rfc-editor.org/rfc/rfc6455)
- The browser `WebSocket` API exposes `send()` for text and binary data and delivers incoming messages through `message` events. `send()` enqueues data for transmission; `bufferedAmount` reports bytes queued but not yet transmitted. The API's `readyState` distinguishes CONNECTING, OPEN, CLOSING, and CLOSED; applications should send only when OPEN and handle `open`, `message`, `error`, and `close` events.
  Source: [WHATWG WebSockets Standard](https://websockets.spec.whatwg.org/); [MDN: WebSocket](https://developer.mozilla.org/en-US/docs/Web/API/WebSocket)
- The standard browser `WebSocket` API has no receive-side backpressure mechanism. If messages arrive faster than application code can process them, buffering and resource use can grow; MDN explicitly notes this limitation. `bufferedAmount` concerns outgoing queued bytes, not incoming data, and is not a complete flow-control mechanism. Applications needing bounded processing must implement application-level pacing/flow control or use another API where appropriate.
  Source: [MDN: WebSocket](https://developer.mozilla.org/en-US/docs/Web/API/WebSocket); [WHATWG WebSockets Standard](https://websockets.spec.whatwg.org/)
- RFC 6455 frames messages and permits fragmentation; control frames (including Ping, Pong, and Close) have protocol-defined handling and may be interjected between fragments. A receiver should treat a complete WebSocket message as the API-level unit rather than assume a frame corresponds to a streamed token. Browser APIs generally expose reassembled messages, not raw frame boundaries.
  Source: [RFC 6455, sections 5.4–5.5](https://www.rfc-editor.org/rfc/rfc6455); [WHATWG WebSockets Standard](https://websockets.spec.whatwg.org/)
- The browser API's `close()` initiates a closing handshake; the `close` event reports closure and includes status/reason information. A connection can close due to normal application action or failure, so streaming clients should handle termination and avoid treating a close as proof that the full response was received unless the application protocol confirms completion.
  Source: [WHATWG WebSockets Standard](https://websockets.spec.whatwg.org/); [MDN: WebSocket close event](https://developer.mozilla.org/en-US/docs/Web/API/WebSocket/close_event)
- Operationally, WebSocket Ping/Pong control frames are defined for keepalive/responsiveness checks at the protocol level, but browser JavaScript does not expose a direct API to send or observe these control frames. Any application-level heartbeat or reconnect policy therefore needs to be designed at the application layer and should not be confused with RFC control frames.
  Source: [RFC 6455, section 5.5.2–5.5.3](https://www.rfc-editor.org/rfc/rfc6455); [WHATWG WebSockets Standard](https://websockets.spec.whatwg.org/)

## Evidence and uncertainty
The search service returned quota/rate-limit errors for all three attempted searches, so findings were compiled from established primary-source URLs and documented standards/API behavior rather than verified live search-result snippets. RFC 6455 and the WHATWG standard are normative protocol/platform sources; MDN is explanatory documentation. Exact buffering limits, network/proxy timeout behavior, and delivery latency are implementation- and deployment-dependent and are not specified as universal guarantees by these sources. The protocol does not guarantee application-level token boundaries, completion semantics, or automatic recovery after disconnection.

## References
- [RFC 6455: The WebSocket Protocol](https://www.rfc-editor.org/rfc/rfc6455)
- [WHATWG WebSockets Standard](https://websockets.spec.whatwg.org/)
- [MDN: WebSocket](https://developer.mozilla.org/en-US/docs/Web/API/WebSocket)
- [MDN: WebSocket close event](https://developer.mozilla.org/en-US/docs/Web/API/WebSocket/close_event)
