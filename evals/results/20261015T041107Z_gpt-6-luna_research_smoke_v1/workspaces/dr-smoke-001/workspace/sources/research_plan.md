# Research Plan

## Research question
Assess trade-offs between Server-Sent Events (SSE) and WebSockets for streaming LLM responses in browser-based AI assistants, emphasizing protocol behavior, browser/runtime support, operational constraints, and practical recommendations. Prefer primary technical documentation.

## Focused researcher assignments and distinct target pages
1. **SSE protocol and browser API** — researcher to examine event-stream semantics, reconnection, event IDs, and browser `EventSource` constraints. Target source page: WHATWG HTML Living Standard, Server-sent events section (`https://html.spec.whatwg.org/multipage/server-sent-events.html`). Output: `/workspace/sources/findings_sse_protocol.md`.
2. **WebSocket protocol and browser API** — researcher to examine bidirectional framing, browser WebSocket API behavior, and protocol-level characteristics. Target source page: WHATWG WebSockets Standard (`https://websockets.spec.whatwg.org/`). Output: `/workspace/sources/findings_websocket_protocol.md`.
3. **LLM streaming implementation and operational guidance** — researcher to examine primary vendor/framework documentation for streaming response patterns and transport-specific operational considerations. Target source page: OpenAI API streaming guide (`https://platform.openai.com/docs/guides/streaming-responses`). Output: `/workspace/sources/findings_llm_streaming.md`.

## Additional distinct primary-source pages to verify if needed
- MDN EventSource API reference: `https://developer.mozilla.org/en-US/docs/Web/API/EventSource`.
- MDN WebSocket API reference: `https://developer.mozilla.org/en-US/docs/Web/API/WebSocket`.
- RFC 6455, The WebSocket Protocol: `https://www.rfc-editor.org/rfc/rfc6455`.
- MDN Using server-sent events: `https://developer.mozilla.org/en-US/docs/Web/API/Server-sent_events/Using_server-sent_events`.

Each source page is a distinct page; fragments do not count as separate sources. Findings must preserve exact URLs returned by successful search/fetch results. Before analysis or drafting, count distinct in-run source pages recorded in findings and add focused evidence under a new findings path if fewer than five.