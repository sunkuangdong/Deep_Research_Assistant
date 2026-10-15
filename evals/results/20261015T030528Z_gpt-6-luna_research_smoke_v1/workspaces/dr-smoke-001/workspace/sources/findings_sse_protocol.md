# Findings: SSE Protocol and Browser EventSource Behavior

## Scope
This research covers the Server-Sent Events (SSE) wire format and browser `EventSource` behavior, including event framing, directionality, reconnection and event IDs, browser API constraints, and implications for LLM token streaming. It does not assess alternative streaming protocols.

## Key findings
- **Event framing:** Browser `EventSource` consumes a persistent HTTP response with the `text/event-stream` media type. The stream is UTF-8 text organized as fields on separate lines; a blank line terminates and dispatches an event. `data` lines form the event payload, multiple data lines are joined with newline characters, `event` selects a named event type (otherwise the generic `message` event is used), and comment lines can serve as keep-alives. A server must frame token updates as SSE events rather than emit arbitrary JSON/text chunks and expect the browser API to parse them as messages.
  Evidence: MDN describes the persistent HTTP connection, `text/event-stream` format, and named versus generic message events. The search did not return the relevant WHATWG event-stream section itself, so detailed field/framing rules are not independently verified here against the standard.
  Source: [MDN EventSource](https://developer.mozilla.org/en-US/docs/Server-sent_events/EventSource)

- **One-way nature:** SSE delivers data messages from server to client; it is not a bidirectional messaging channel like WebSocket. An LLM application can stream generated output to the browser over SSE, but user prompts, cancellation, tool input, and other client-to-server actions need a separate HTTP request or another channel.
  Evidence: MDN explicitly characterizes server-sent events as unidirectional, from server to client.
  Source: [MDN EventSource](https://developer.mozilla.org/en-US/docs/Server-sent_events/EventSource)

- **Reconnection and event IDs:** `EventSource` maintains a persistent connection and reconnects after eligible connection failures. SSE `id` values support resumption: the browser tracks the last event ID and can send it as `Last-Event-ID` on a reconnect. This is a cursor, not a replay guarantee: the server must retain or otherwise be able to retrieve events and honor the cursor. Reconnection alone does not ensure exactly-once delivery or prevent gaps/duplicates; applications should define replay and deduplication semantics.
  Evidence: MDN confirms the persistent connection and that it remains open until `close()`; the search results did not return the relevant WHATWG reconnection/ID section. The resume behavior and its server-side dependency are therefore not fully corroborated by the retrieved primary-source excerpts.
  Source: [MDN EventSource](https://developer.mozilla.org/en-US/docs/Server-sent_events/EventSource)

- **Browser API constraints:** The native API is constructed with a URL and optional credentials mode; it exposes connection state and event handlers, and `close()` terminates the connection. It is an event-stream consumer, not a general-purpose streaming `fetch`: the standard constructor does not provide a general custom-request-header option or a request body. This can constrain authenticated LLM endpoints that require bearer headers or POSTed prompts; common designs use same-site cookies/credentials, a short-lived URL token where appropriate, or POST the prompt separately and open an SSE stream for the resulting job. Cross-origin use is subject to CORS and credentials configuration.
  Evidence: MDN search excerpt confirms the URL-based persistent connection and `close()` behavior. The returned excerpt does not expose the full constructor/API constraints, so those details should be checked against the complete API documentation before implementation decisions.
  Source: [MDN EventSource](https://developer.mozilla.org/en-US/docs/Server-sent_events/EventSource)

- **Implications for LLM token streaming:** SSE is a natural fit for incremental, server-to-browser text or structured updates when the client primarily receives output. The server should emit each token or logical update as a complete `data:` event, optionally use named events for lifecycle/status/error messages, and send a terminal event or close the stream when generation finishes. Token-level events can incur framing and event-dispatch overhead; batching small token fragments can reduce overhead at the cost of perceived latency. If reconnect/resume matters, assign stable sequence IDs and implement server-side replay; otherwise a reconnect may restart or leave an incomplete answer. Client-to-server controls such as stop-generation remain separate requests.
  Evidence: These are design implications derived from the documented one-way persistent event delivery and event-type behavior; the search results did not include an LLM-specific primary source.
  Source: [MDN EventSource](https://developer.mozilla.org/en-US/docs/Server-sent_events/EventSource)

## Evidence and uncertainty
The search returned an MDN EventSource page with a complete URL and an HTML Standard page, but the WHATWG results were unrelated sections rather than the Server-sent events section. The MDN excerpt supports the persistent connection, `text/event-stream`, event dispatch, one-way delivery, and explicit close behavior. Detailed framing, reconnection timing, `Last-Event-ID`, and constructor limitations are not fully evidenced by the returned excerpts; these are stated with that limitation and should be verified against the relevant full standard/API text before relying on edge-case behavior. No LLM-specific source was retrieved; the LLM guidance is protocol-level engineering inference.

## References
- [MDN EventSource](https://developer.mozilla.org/en-US/docs/Server-sent_events/EventSource)
- [WHATWG HTML Standard search result (returned section is not the SSE section)](https://html.spec.whatwg.org/multipage/iana.html)
