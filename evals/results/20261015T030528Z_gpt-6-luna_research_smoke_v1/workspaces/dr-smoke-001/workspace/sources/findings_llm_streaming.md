# Findings: LLM Streaming and Browser HTTP Transport Considerations

## Scope
This research covers how LLM APIs expose streamed output and the browser-side HTTP considerations relevant to choosing Server-Sent Events (SSE) or WebSockets for an AI assistant. It focuses on event framing, cancellation and errors, and practical transport implications. It does not make comparative performance claims.

## Key findings
- **Streaming is an application-level sequence, not just a connection type.** An LLM streaming API can emit multiple structured events over a response stream; the client must parse the provider's event framing and distinguish incremental content from completion and error signals. The search did not return official OpenAI or Anthropic streaming documentation, so provider-specific event names and exact wire formats are not verified here.
  Source: No official provider source was returned in the searches.
- **Fetch cancellation can stop both the request and response-body consumption.** The browser `AbortController.abort()` method can abort fetch requests, response-body consumption, and streams. This supports a user-facing “stop generating” action when the browser is consuming an HTTP stream; the application should also treat abort as a distinct client-side termination rather than assuming it is a provider error.
  Source: [MDN: AbortController: abort() method](https://developer.mozilla.org/en-US/docs/Web/API/AbortController/abort)
- **Transport choice does not remove the need for explicit error and lifecycle handling.** A browser client should handle HTTP response status before consuming the body, parse stream-level error/completion events where the provider defines them, and handle network interruption or user cancellation. The returned sources establish Fetch abort behavior, but do not document provider-specific retry semantics or error-event schemas.
  Source: [MDN: AbortController: abort() method](https://developer.mozilla.org/en-US/docs/Web/API/AbortController/abort)
- **Practical implication for browser assistants:** HTTP streaming via Fetch is compatible with request bodies and browser abort signaling, which is useful when a prompt is submitted as a POST and the user may cancel generation. SSE is an event-stream framing convention over HTTP; WebSockets instead require a persistent bidirectional protocol and application-defined message handling. The searches did not return authoritative primary documentation sufficient to substantiate detailed SSE-versus-WebSocket browser constraints, so this distinction should be treated as a high-level architectural observation, not a complete compatibility comparison.
  Source: [MDN: AbortController: abort() method](https://developer.mozilla.org/en-US/docs/Web/API/AbortController/abort)

## Evidence and uncertainty
Evidence is limited. The searches did not return official OpenAI or Anthropic streaming documentation, nor authoritative primary documentation for SSE/EventSource or WebSockets. The only directly relevant primary source returned was MDN's AbortController documentation. Consequently, provider event formats, keep-alive/reconnection behavior, authentication constraints, proxy buffering, and transport performance are not established by this research. No unsupported performance claims are made.

## Reference sources
- [MDN: AbortController: abort() method](https://developer.mozilla.org/en-US/docs/Web/API/AbortController/abort)
