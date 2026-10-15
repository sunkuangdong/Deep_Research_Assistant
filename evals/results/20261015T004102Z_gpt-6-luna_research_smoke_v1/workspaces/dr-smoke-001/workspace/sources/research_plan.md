# Research Plan

## Main question
Assess the trade-offs between Server-Sent Events (SSE) and WebSockets for streaming LLM responses in browser-based AI assistants, using primary technical documentation where available and recommending appropriate use cases.

## Subtopics and outputs
1. **SSE protocol and browser/runtime behavior** — document event framing, one-way delivery, reconnection, browser API constraints, and HTTP implications. Output: `/workspace/sources/findings_sse.md`.
2. **WebSocket protocol and browser/runtime behavior** — document full-duplex semantics, connection lifecycle, browser API constraints, and operational implications. Output: `/workspace/sources/findings_websockets.md`.
3. **LLM streaming application patterns and decision factors** — examine how streaming generation, cancellation, tool/status events, authentication, proxies, and deployment shape transport choice, grounding claims in primary documentation where possible. Output: `/workspace/sources/findings_llm_patterns.md`.

## Synthesis strategy
Compare the transports across directionality, implementation complexity, latency/overhead, reconnection and reliability, infrastructure compatibility, security/authentication, and fit for LLM assistant interaction patterns. Distinguish protocol facts from application-level design recommendations, and state uncertainty where primary documentation does not establish comparative performance.