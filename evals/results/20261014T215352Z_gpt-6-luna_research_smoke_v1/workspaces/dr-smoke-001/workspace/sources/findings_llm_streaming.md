# Findings: Application-Level Implications of SSE vs WebSockets for Browser-Based LLM Response Streaming

## Research scope
This note compares Server-Sent Events (SSE) and WebSockets only as application transports for browser-based LLM response streaming. It covers token/event delivery, cancellation, tool and control messages, authentication/security, proxy compatibility, and practical patterns. It does not compare model quality or general-purpose real-time systems. The requested web searches did not return usable source results, so the findings below rely on established API and browser behavior and include direct primary-source URLs for verification; provider-specific details should be checked against the current documentation.

## Key findings

- **SSE is a natural fit for one-way model output and typed event streams.** The browser `EventSource` API consumes a persistent HTTP response formatted as `text/event-stream`; events can carry named event types and data, which maps well to incremental text deltas, completion markers, usage metadata, and structured response lifecycle events. OpenAI's Responses API documents streaming via server-sent events and event types, while Anthropic documents streaming messages over HTTP using SSE.
  - Documented fact: SSE is an HTTP event-stream format and browser EventSource is a server-to-browser event interface; provider APIs expose typed streaming events.
  - Application inference: for a typical prompt-submit → token-stream → completion flow, SSE avoids maintaining a bidirectional socket when the browser has no need to send ongoing messages during generation.
  - Sources: [OpenAI Responses API streaming](https://platform.openai.com/docs/guides/streaming-responses), [Anthropic streaming messages](https://docs.anthropic.com/en/api/messages-streaming), [MDN EventSource](https://developer.mozilla.org/en-US/docs/Web/API/EventSource), [WHATWG HTML: Server-sent events](https://html.spec.whatwg.org/multipage/server-sent-events.html)

- **WebSockets provide a bidirectional channel, but do not inherently define LLM token or tool semantics.** The browser WebSocket API supports sending and receiving messages over a persistent connection. OpenAI's Realtime API uses WebSockets for client/server real-time interaction and defines its own event protocol. For ordinary text generation, the application must still define message framing, event names, ordering, errors, and completion semantics.
  - Documented fact: WebSocket is bidirectional; provider Realtime APIs define application-level events on top of it.
  - Application inference: WebSockets are useful when the browser must send control/input while generation is active (e.g., interruption, audio, interactive sessions), but are not automatically lower-latency or simpler for a one-way text stream; actual performance depends on implementation and network path.
  - Sources: [MDN WebSocket](https://developer.mozilla.org/en-US/docs/Web/API/WebSocket), [OpenAI Realtime API guide](https://platform.openai.com/docs/guides/realtime)

- **Token streaming is usually event streaming, not a guaranteed one-token-per-message contract.** Provider streams commonly expose deltas and lifecycle events; a delta may contain a fragment rather than exactly one model token. Applications should append text fragments, handle non-text events, and treat explicit completion/error events as authoritative rather than infer completion from a pause or socket close.
  - Documented fact: OpenAI and Anthropic document event-based streaming and distinct event types/deltas.
  - Application inference: UI code should be resilient to arbitrary chunk boundaries, partial UTF-8/text fragments, and interleaved metadata; do not equate transport frames with tokenizer tokens.
  - Sources: [OpenAI Responses API streaming](https://platform.openai.com/docs/guides/streaming-responses), [Anthropic streaming messages](https://docs.anthropic.com/en/api/messages-streaming)

- **Cancellation is an application operation, not merely a transport close.** With fetch-based SSE, the browser can abort the request using `AbortController`; closing an `EventSource` stops its connection. With WebSockets, the client can send an application-defined cancel/interrupt event or close the socket. In either case, the server/provider may need explicit cancellation propagation to stop generation and release work; disconnecting the browser alone does not prove upstream generation stopped.
  - Documented fact: Fetch supports abort signals; EventSource can be closed; WebSocket supports close and message send.
  - Application inference: implement cancellation end-to-end (UI → application server → provider request), and distinguish “client stopped receiving” from “generation was cancelled.” Prefer a cancel event for a multiplexed/long-lived WebSocket session where closing the whole connection would discard unrelated session state.
  - Sources: [MDN AbortController](https://developer.mozilla.org/en-US/docs/Web/API/AbortController), [MDN EventSource.close](https://developer.mozilla.org/en-US/docs/Web/API/EventSource/close), [MDN WebSocket](https://developer.mozilla.org/en-US/docs/Web/API/WebSocket)

- **Tool calls and control messages require explicit protocol handling regardless of transport.** LLM APIs may emit tool-call or other structured events as part of a response stream. SSE can carry these as named/data events in the server-to-browser direction, but browser-to-server tool results or user controls require a separate HTTP request/channel. WebSockets can carry both directions on one connection, but the application must define correlation IDs, sequencing, acknowledgements, and authorization for each event.
  - Documented fact: provider streaming protocols include structured events beyond text; WebSockets are bidirectional.
  - Application inference: keep tool execution and privileged actions server-side where possible; treat model-emitted tool requests as untrusted proposals, validate arguments and permissions, and return tool results through a correlated server-side workflow. A WebSocket does not make tool execution safe by itself.
  - Sources: [OpenAI Responses API streaming](https://platform.openai.com/docs/guides/streaming-responses), [OpenAI function calling](https://platform.openai.com/docs/guides/function-calling), [MDN WebSocket](https://developer.mozilla.org/en-US/docs/Web/API/WebSocket)

- **Browser authentication ergonomics differ.** Native `EventSource` exposes a URL and `withCredentials` option but does not provide a general arbitrary-header configuration surface; fetch-based streaming can attach authorization headers and use `AbortController`. WebSocket browser construction likewise does not expose arbitrary request headers in the standard constructor; cookie-based authentication, short-lived connection tickets, or a same-origin backend proxy are common patterns. Avoid putting long-lived API keys or bearer credentials in query strings, which can leak through logs, history, and telemetry.
  - Documented fact: EventSource and WebSocket browser APIs have constrained constructor options; Fetch supports request headers; credentialed cross-origin requests are subject to browser CORS/credential rules.
  - Application inference: for browser-to-provider access, a backend proxy or narrowly scoped short-lived token is generally safer than embedding a provider secret. Validate WebSocket `Origin`, authenticate the session, and authorize each operation; CORS alone is not WebSocket authorization.
  - Sources: [MDN EventSource](https://developer.mozilla.org/en-US/docs/Web/API/EventSource), [MDN WebSocket](https://developer.mozilla.org/en-US/docs/Web/API/WebSocket), [MDN Fetch](https://developer.mozilla.org/en-US/docs/Web/API/Fetch_API), [OWASP WebSocket Security Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/WebSocket_Security_Cheat_Sheet.html)

- **Proxy and platform compatibility is deployment-dependent.** SSE uses ordinary HTTP responses and is often easier to route through HTTP infrastructure, but buffering, response compression, idle timeouts, and intermediary behavior can delay or interrupt events unless configured for streaming. WebSockets require upgrade/tunnel support and may encounter platform-specific connection-duration, idle-timeout, or scaling constraints. Official cloud documentation should be checked for the exact hosting path rather than assuming either transport always works.
  - Documented fact: cloud platforms document distinct WebSocket support and timeout/connection constraints; HTTP streaming behavior can be affected by intermediaries.
  - Application inference: test through the actual CDN, load balancer, serverless runtime, and corporate proxy. For SSE, disable buffering where required and send periodic comments/heartbeats if appropriate; for WebSockets, implement reconnect/resume and heartbeat behavior. Neither transport guarantees replay of missed application events without an application-level cursor or session protocol.
  - Sources: [Cloudflare WebSockets](https://developers.cloudflare.com/network/websockets/), [AWS API Gateway WebSocket APIs](https://docs.aws.amazon.com/apigateway/latest/developerguide/apigateway-websocket-api.html), [MDN SSE guide](https://developer.mozilla.org/en-US/docs/Web/API/Server-sent_events/Using_server-sent_events)

- **Practical patterns:**
  - Use **fetch + SSE parsing** when the browser needs POST bodies, custom authorization headers, and abort control for a single generation request. This is often more flexible than native `EventSource` for authenticated LLM APIs.
  - Use **native EventSource** when a GET-based, cookie-authenticated, server-to-browser event stream and its built-in reconnection behavior fit the application; account for its limited request customization and reconnection semantics.
  - Use **WebSockets** when the product needs sustained bidirectional interaction (e.g., real-time audio, frequent user controls, multiplexed session events) and the hosting path supports upgrades reliably.
  - Use a **backend proxy** for provider credentials, policy enforcement, tool execution, rate limiting, and normalization of provider-specific event formats. These are application recommendations inferred from the documented API and browser constraints, not provider mandates.
  - Sources: [OpenAI streaming guide](https://platform.openai.com/docs/guides/streaming-responses), [OpenAI Realtime guide](https://platform.openai.com/docs/guides/realtime), [MDN EventSource](https://developer.mozilla.org/en-US/docs/Web/API/EventSource), [MDN WebSocket](https://developer.mozilla.org/en-US/docs/Web/API/WebSocket)

## Evidence and uncertainty
The requested search tool returned no usable search results, so this memo could not verify current wording, feature availability, or provider-specific event names against live pages during this run. The cited URLs are primary or official documentation entry points, but individual pages may change. The distinction between documented facts and application inferences is stated in each finding. Proxy behavior is especially deployment-specific; validate buffering, idle timeouts, reconnect behavior, and WebSocket upgrade support in the actual production path. No universal claim is made that SSE or WebSockets is categorically faster or more reliable.

## References
- [OpenAI Responses API streaming](https://platform.openai.com/docs/guides/streaming-responses)
- [OpenAI Realtime API guide](https://platform.openai.com/docs/guides/realtime)
- [OpenAI function calling](https://platform.openai.com/docs/guides/function-calling)
- [Anthropic streaming messages](https://docs.anthropic.com/en/api/messages-streaming)
- [WHATWG HTML: Server-sent events](https://html.spec.whatwg.org/multipage/server-sent-events.html)
- [MDN EventSource](https://developer.mozilla.org/en-US/docs/Web/API/EventSource)
- [MDN Server-sent events guide](https://developer.mozilla.org/en-US/docs/Web/API/Server-sent_events/Using_server-sent_events)
- [MDN WebSocket](https://developer.mozilla.org/en-US/docs/Web/API/WebSocket)
- [MDN AbortController](https://developer.mozilla.org/en-US/docs/Web/API/AbortController)
- [MDN Fetch API](https://developer.mozilla.org/en-US/docs/Web/API/Fetch_API)
- [OWASP WebSocket Security Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/WebSocket_Security_Cheat_Sheet.html)
- [Cloudflare WebSockets](https://developers.cloudflare.com/network/websockets/)
- [AWS API Gateway WebSocket APIs](https://docs.aws.amazon.com/apigateway/latest/developerguide/apigateway-websocket-api.html)
