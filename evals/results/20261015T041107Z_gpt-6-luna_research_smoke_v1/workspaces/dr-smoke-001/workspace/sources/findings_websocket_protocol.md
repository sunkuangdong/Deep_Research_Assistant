# Findings: WebSocket Protocol and Browser API for LLM Streaming

## Research scope
This file covers only WebSocket protocol and browser WebSocket API behavior relevant to streaming LLM responses: bidirectional communication, message/framing semantics, browser API constraints, and operational implications. It does not investigate SSE as a separate topic.

## Key findings
- **WebSocket provides a persistent, bidirectional channel.** After an opening handshake, the protocol carries data in both directions over one TCP connection; either endpoint can independently send data. This supports sending prompts/control messages upstream while receiving generated output downstream, and allows interactive actions such as cancellation or follow-up input on the same connection. The browser API is not raw network access: it exposes WebSocket operations rather than arbitrary socket bytes.
  Source: [RFC 6455: The WebSocket Protocol](https://www.rfc-editor.org/info/rfc6455/); [WebSockets Standard](https://websockets.spec.whatwg.org/)

- **Frames and messages are distinct; application message boundaries matter.** RFC 6455 defines framing, including text and binary data frames, fragmentation, and control frames. A fragmented message may span multiple frames, and control frames can be interjected during fragmentation. Browser scripts receive complete WebSocket messages through `message` events, not individual protocol frames. Consequently, a server can emit successive text messages as incremental LLM updates, but splitting one logical message into protocol frames does not itself expose incremental frame chunks to JavaScript. Application-level chunking should therefore use separate messages (or an explicit application protocol) when the client needs to process partial output as it arrives.
  Source: [RFC 6455: The WebSocket Protocol](https://www.rfc-editor.org/info/rfc6455/); [WebSockets Standard](https://websockets.spec.whatwg.org/)

- **The browser API supports text and binary payloads, but has no built-in streaming/backpressure reader.** `send()` accepts strings, `Blob`, `ArrayBuffer`, and `ArrayBufferView`; incoming text is exposed as a string, while binary data is exposed as `Blob` by default or `ArrayBuffer` when `binaryType` is changed. The standard exposes `bufferedAmount`, the number of application-data bytes queued by `send()` but not yet transmitted. It does not provide a `ReadableStream`-style per-chunk receive interface or a promise indicating that a send has reached the network. For LLM clients, monitor `bufferedAmount` for outbound congestion and design application-level flow control if needed; do not treat it as a measure of server processing or inbound backlog.
  Source: [WebSockets Standard](https://websockets.spec.whatwg.org/)

- **Connection setup and lifecycle are explicit constraints.** The constructor accepts `ws`/`wss` (and corresponding `http`/`https` forms that are converted), rejects fragments and invalid schemes, and can negotiate named subprotocols. The connection progresses through `CONNECTING`, `OPEN`, `CLOSING`, and `CLOSED`; `send()` while not open is not a reliable way to queue application work. The standard’s handshake integrates with Fetch, includes credentials mode `include`, disallows redirects, and uses the browser security model. Applications should wait for `open`, handle `error`/`close`, and implement reconnect/resume behavior where generation continuity matters.
  Source: [WebSockets Standard](https://websockets.spec.whatwg.org/)

- **Operationally, WebSocket does not define LLM token semantics or delivery/resumption.** The protocol transports messages; it does not specify token boundaries, generation identifiers, replay after disconnect, acknowledgements, or cancellation semantics. Those must be defined by the application protocol. A robust streaming design should distinguish incremental content, completion, errors, and cancellation; associate updates with a request/generation ID; and decide whether reconnect means restart or resume. RFC 6455 also notes that interactive messaging traffic can impose unusual loads on infrastructure, so connection duration, concurrency, and server-side resource limits are relevant operational considerations.
  Source: [RFC 6455: The WebSocket Protocol](https://www.rfc-editor.org/info/rfc6455/)

## Evidence and uncertainty
Evidence is based on the WHATWG WebSockets Standard (the assigned primary browser API specification) and RFC 6455 (the protocol standard). The WHATWG page explicitly defines the browser interface, message events, send types, lifecycle states, and `bufferedAmount`; RFC 6455 describes the bidirectional connection and framing/fragmentation model. The operational recommendations are implications of those documented behaviors, not requirements imposed by either standard. Neither source specifies LLM-specific chunking, token delivery, replay, or application-level flow control. Browser implementations and network intermediaries may also impose practical limits not quantified here; the cited specifications do not establish universal throughput or latency guarantees.

## References
- [WebSockets Standard](https://websockets.spec.whatwg.org/)
- [RFC 6455: The WebSocket Protocol](https://www.rfc-editor.org/info/rfc6455/)
