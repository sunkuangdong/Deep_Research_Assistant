# Findings: WebSocket Protocol and Browser API Behavior

## Scope
This research covers only the WebSocket protocol and the browser WebSocket API: full-duplex communication, connection/handshake and message basics, browser API constraints including buffering and backpressure, and implications for LLM streaming. It does not assess particular WebSocket libraries or application frameworks.

## Key findings

- **WebSocket provides a persistent, two-way communication channel.** RFC 6455 describes a protocol for two-way communication between a client and server over a single TCP connection. After a successful opening handshake, either endpoint can independently send data; this supports server-initiated updates without repeated HTTP polling. The channel is full-duplex, but that does not itself guarantee low latency, delivery to application code, or application-level flow control.
  Evidence: Search results for RFC 6455 describe the protocol as two-way communication over TCP and state that after the handshake each endpoint can independently send data. The search did not return the RFC Editor page itself, so the available result is a secondary source.
  Source: [RFC 6455 listing and summary](https://www.antpedia.com/standard/2001864819.html)

- **The protocol begins with an opening handshake and then uses framed messages.** RFC 6455’s protocol structure is an opening handshake followed by data framing over TCP. The handshake establishes the WebSocket connection; subsequent communication uses WebSocket frames/messages rather than treating each application message as a separate HTTP request. The search result also identifies data frames and control frames (including ping/pong) as protocol elements. The exact handshake header requirements and frame-field details were not independently verified from an official RFC result in this search run.
  Evidence: Search results summarize RFC 6455 as an opening handshake plus basic message framing over TCP and mention data and control frames.
  Source: [RFC 6455 listing and summary](https://www.antpedia.com/standard/2001864819.html)

- **The browser `WebSocket` API exposes connection management and message send/receive, but has no receive-side backpressure mechanism.** MDN states that the API creates/manages a WebSocket connection and sends and receives data. It explicitly warns that the API has no way to apply backpressure: if messages arrive faster than the application processes them, buffering can consume device memory and/or high CPU can make the page unresponsive.
  Evidence: MDN’s WebSocket API page states the API’s purpose and the lack of backpressure, including the potential memory and responsiveness consequences.
  Source: [MDN: WebSocket](https://developer.mozilla.org/en-US/docs/Web/API/WebSocket)

- **Implications for LLM streaming:** WebSocket is suitable when an LLM application needs a persistent bidirectional channel—for example, to stream generated output while also allowing the client to send cancellation, interaction, or control messages. However, the browser API’s lack of receive-side backpressure means the application should avoid unboundedly queuing incoming tokens/events when rendering or downstream processing is slower than arrival. Practical designs should bound application queues, batch/coalesce UI updates where appropriate, and define cancellation or overload behavior. These are engineering implications inferred from the documented API limitation, not guarantees or recommendations stated by RFC 6455 or MDN.

## Evidence and uncertainty
The MDN result is a primary documentation source and directly supports the browser API and backpressure findings. The search for RFC 6455 did not return an official RFC Editor or IETF URL; the protocol findings therefore rely on a secondary listing/summary and should be checked against the RFC text before making claims about exact handshake fields, masking rules, fragmentation, or control-frame requirements. The search results do not establish LLM-specific performance or behavior; those implications are reasoned from the documented bidirectional channel and browser buffering limitation. No claim is made here about `bufferedAmount` semantics because the returned MDN result did not document it.

## Reference sources
- [RFC 6455 listing and summary](https://www.antpedia.com/standard/2001864819.html)
- [MDN: WebSocket](https://developer.mozilla.org/en-US/docs/Web/API/WebSocket)
