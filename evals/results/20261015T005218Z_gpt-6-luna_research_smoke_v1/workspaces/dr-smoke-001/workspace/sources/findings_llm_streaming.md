# Findings: LLM streaming implementation context in browser-based AI assistants

## Research scope
This note covers browser-facing LLM response streaming, focusing on provider-documented HTTP/SSE behavior, event framing, browser cancellation, and practical HTTP/proxy considerations. It does not compare SSE and WebSockets except to note the one-way server-to-client nature relevant to response delivery.

## Key findings
- **Provider APIs commonly expose streaming as an option on an ordinary HTTP request, with the response delivered as SSE.** Anthropic explicitly documents setting `stream: true` on a Messages request to incrementally stream the response using server-sent events. Its events have named SSE event types and JSON data; the documented lifecycle includes `message_start`, content-block start/delta/stop events, and message completion events. This is a provider-specific event schema, not just arbitrary text chunks.  
  Source: [Anthropic — Streaming Messages](https://docs.anthropic.com/en/api/messages-streaming)

- **SSE framing is event-oriented, not equivalent to one network chunk per model token or event.** The W3C EventSource specification defines an HTTP event stream and its parsing model. SSE uses UTF-8 text with fields such as `event:` and `data:`; a blank line terminates an event, and multiple `data:` lines are joined. Implementations must parse incrementally across arbitrary transport chunk boundaries. Provider payloads may themselves be JSON inside `data:`.  
  Source: [W3C — Server-Sent Events](https://www.w3.org/TR/2015/REC-eventsource-20150203/)

- **Browser clients often use `fetch()` plus a streaming response reader when they need POST bodies, custom authorization headers, or explicit request control.** Native `EventSource` is designed around opening an event-stream URL; provider generation requests commonly need a JSON POST body and authorization. A browser app therefore often calls its own backend, or uses `fetch` and incrementally parses the response body. This is an implementation pattern inferred from the API shape and browser APIs, not a universal provider mandate.  
  Sources: [Anthropic — Streaming Messages](https://docs.anthropic.com/en/api/messages-streaming), [MDN — AbortController.abort()](https://developer.mozilla.org/en-US/docs/Web/API/AbortController/abort)

- **Cancellation is available at the browser request/stream level, but stopping client consumption is not proof that generation stopped upstream.** MDN documents that `AbortController.abort()` can abort fetch requests, response-body consumption, and streams. In a browser assistant, pass an `AbortSignal` to `fetch` and abort it on user stop/navigation. Whether the provider or intermediary promptly halts model generation and billing is dependent on server-side disconnect propagation and provider behavior; the cited provider streaming documentation does not establish a universal guarantee.  
  Source: [MDN — AbortController.abort()](https://developer.mozilla.org/en-US/docs/Web/API/AbortController/abort)

- **HTTP intermediaries can affect perceived streaming.** The application needs an end-to-end path that flushes response bytes rather than buffering them until completion. Reverse proxies, gateways, compression middleware, server frameworks, and hosting platforms may buffer or coalesce output; configure and test the actual deployment path. SSE responses conventionally use `Content-Type: text/event-stream`; keep the response open while events are emitted. The sources found establish the SSE media type/HTTP event-stream model, but do not provide a single provider-independent proxy configuration or guarantee against buffering.  
  Sources: [W3C — Server-Sent Events](https://www.w3.org/TR/2015/REC-eventsource-20150203/), [Anthropic — Streaming Messages](https://docs.anthropic.com/en/api/messages-streaming)

- **Provider documentation does not establish a universal transport recommendation for browser assistants.** Anthropic documents SSE for its Messages streaming endpoint. The available search results did not surface a verifiable OpenAI primary streaming documentation page, so no claim is made here about OpenAI’s current transport details or a cross-provider standard. Provider docs describe their own API contract; they do not, on the evidence reviewed, prescribe SSE as the universal choice for all browser-based assistants.  
  Sources: [Anthropic — Streaming Messages](https://docs.anthropic.com/en/api/messages-streaming), [W3C — Server-Sent Events](https://www.w3.org/TR/2015/REC-eventsource-20150203/)

## Evidence and uncertainty
Evidence is strongest for Anthropic’s explicit SSE contract, the W3C SSE event-stream specification, and MDN’s browser cancellation API description. Search results did not yield a primary OpenAI streaming documentation URL that could be verified, so OpenAI-specific framing and terminal markers are intentionally omitted. Proxy buffering guidance is an operational implication of streaming over HTTP rather than a provider-specific guarantee; behavior varies by infrastructure and should be validated in deployment. Cancellation reliably describes browser-side abort capability, but upstream generation termination and cost effects are not guaranteed by the cited sources. The W3C document is a formal SSE specification; browser implementations and provider-specific event schemas may add practical details.

## References
- [Anthropic — Streaming Messages](https://docs.anthropic.com/en/api/messages-streaming)
- [W3C — Server-Sent Events](https://www.w3.org/TR/2015/REC-eventsource-20150203/)
- [MDN — AbortController.abort()](https://developer.mozilla.org/en-US/docs/Web/API/AbortController/abort)
