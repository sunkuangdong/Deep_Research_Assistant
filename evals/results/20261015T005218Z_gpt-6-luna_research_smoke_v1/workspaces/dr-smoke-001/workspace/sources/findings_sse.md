# Findings: SSE Protocol and Browser Behavior for Streaming LLM Responses

## Research scope
This file covers only the Server-Sent Events (SSE) wire format and browser `EventSource` behavior relevant to streaming LLM responses: one-way delivery, request constraints, reconnection and event IDs, cancellation, and practical implications. It does not cover alternative streaming protocols.

## Key findings
- **SSE is a one-way server-to-client event mechanism over an HTTP response.** The browser opens an `EventSource` connection and receives events; application messages from the client to the server are not part of the SSE stream. For LLM applications, this means the generation request and any later user input/control messages need a separate request/channel; SSE itself carries generated output downstream.
  Source: [W3C Server-Sent Events Recommendation](https://www.w3.org/TR/2015/REC-eventsource-20150203/)

- **The event stream is UTF-8 text with media type `text/event-stream`.** Fields are line-oriented; a blank line dispatches an event. Common fields are `data`, `event`, `id`, and `retry`; multiple `data:` lines are joined with newline characters. A comment line beginning with `:` can be used as a keep-alive and is not dispatched as an event. A stream that ends without the terminating blank line does not dispatch its pending event. These framing rules matter for token streams: each logical chunk/event must be correctly delimited, and arbitrary raw JSON or token text must be placed in `data:` lines (often encoded as JSON).
  Source: [W3C Server-Sent Events Recommendation](https://www.w3.org/TR/2015/REC-eventsource-20150203/)

- **Native browser `EventSource` is not a general-purpose request API.** Its constructor takes a URL and optional credentials mode; it does not expose a method/body or arbitrary request-header option. The browser’s EventSource fetch is a GET, so a typical POST-based LLM prompt request, or a request requiring an `Authorization: Bearer ...` header, cannot be sent directly through native `EventSource`. Common design implications are to establish the generation through a separate request and stream by URL, use cookie-based authentication where appropriate, or use a lower-level streaming fetch client when custom method/headers/body are required. Cross-origin credentials are opt-in via the credentials option and still subject to CORS.
  Source: [W3C Server-Sent Events Recommendation](https://www.w3.org/TR/2015/REC-eventsource-20150203/)

- **Reconnection is built into `EventSource`, unless the client closes it or the server response indicates the stream should stop.** The server can provide a `retry:` field (milliseconds) to influence the reconnection delay. An `id:` field updates the event stream’s last-event-ID state; on reconnection the browser sends that value in the `Last-Event-ID` request header. This supports resuming a stream only if the server assigns stable IDs and implements replay/resumption semantics. It does not by itself guarantee exactly-once delivery or prevent duplicate output; LLM clients should make resumed chunks identifiable and handle replay safely.
  Source: [W3C Server-Sent Events Recommendation](https://www.w3.org/TR/2015/REC-eventsource-20150203/)

- **Cancellation is explicit at the browser API level.** Calling `EventSource.close()` closes the connection and sets the object to the closed state, preventing automatic reconnection. This stops the client’s subscription/receipt; it should not be assumed to cancel server-side model generation or billing unless the server ties disconnect detection to generation cancellation. LLM systems should define and test server-side disconnect handling or provide a separate cancellation operation.
  Source: [W3C Server-Sent Events Recommendation](https://www.w3.org/TR/2015/REC-eventsource-20150203/)

- **LLM token streaming is a framing and lifecycle problem, not necessarily one event per model token.** SSE can carry incremental text or structured chunks, but the application chooses chunk granularity. Correct `data:` framing, flush behavior, terminal/error signaling, and a clear policy for reconnecting to an in-progress generation are required. Native EventSource’s GET/header limitations can be decisive when prompts are large or authorization must be supplied in headers; the protocol’s one-way nature also means client-side stop/regenerate actions need a separate mechanism.
  Source: [W3C Server-Sent Events Recommendation](https://www.w3.org/TR/2015/REC-eventsource-20150203/)

## Evidence and uncertainty
The primary source located is the W3C Server-Sent Events Recommendation, which specifies the event-stream format and EventSource processing model. The search did not retrieve the current WHATWG HTML section directly, so this summary cites the W3C Recommendation rather than claiming a line-by-line check against the current living standard. Browser implementations may have practical buffering, proxy timeout, and connection-limit behavior beyond the protocol rules; those deployment-specific details are not established here. The exact server-side effect of a client disconnect on model generation is implementation-dependent and not guaranteed by SSE or `EventSource`.

## References
- [Server-Sent Events — W3C Recommendation](https://www.w3.org/TR/2015/REC-eventsource-20150203/)
- [Server-Sent Events — WHATWG HTML Living Standard](https://html.spec.whatwg.org/multipage/server-sent-events.html)
- [Using server-sent events — MDN](https://developer.mozilla.org/en-US/docs/Web/API/Server-sent_events/Using_server-sent_events)
