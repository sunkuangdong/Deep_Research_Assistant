# Findings: SSE Protocol and Browser EventSource Behavior for LLM Streaming

## Research scope
This file covers only the Server-Sent Events (SSE) event-stream format, the browser `EventSource` API and its reconnection behavior, documented request customization constraints, and implications for streaming LLM responses. It does not investigate WebSockets as a separate topic.

## Key findings
- **SSE is a one-way server-to-client event mechanism over an HTTP response.** The WHATWG introduction describes creating an `EventSource` and registering listeners to receive server-pushed events. The browser API does not define a client-to-server message method; client input must be sent separately if an application needs it. The stream is UTF-8 text, not an arbitrary binary event payload.
  Source: [HTML Standard — Server-sent events](https://html.spec.whatwg.org/multipage/server-sent-events.html)

- **Wire format is line-oriented and blank-line-delimited.** The response uses the `text/event-stream` MIME type. Fields are lines such as `data:`, `event:`, `id:`, and `retry:`; a blank line terminates an event. Multiple `data:` lines are joined with newline characters. Lines beginning with `:` are comments and can be used as keep-alives. The default event type is `message`; `event:` selects a named event. UTF-8 is mandatory. The standard’s examples show multiple events in one continuing response.
  Source: [HTML Standard — Server-sent events](https://html.spec.whatwg.org/multipage/server-sent-events.html)

- **`EventSource` has a deliberately narrow request interface.** Its constructor accepts a URL and an optional `withCredentials` boolean; the standard’s `EventSourceInit` dictionary exposes no method, headers, or body options. The request is created by the browser’s fetch processing, with `Accept: text/event-stream` permitted by the standard and cache mode set to `no-store`. `withCredentials: true` selects credentials mode `include`. Thus native `EventSource` does not provide a documented way to set arbitrary authorization headers or send a POST body; applications needing those controls require a different request mechanism or an application-specific workaround. This conclusion is limited to the standard API surface, not every browser extension or third-party library.
  Source: [HTML Standard — Server-sent events](https://html.spec.whatwg.org/multipage/server-sent-events.html)

- **Reconnection is built in, with resumability support through event IDs.** On a recoverable connection end, the user agent reestablishes the connection after a reconnection delay (which may be implementation-defined and may be increased, e.g. by backoff). A `retry:` field can set the reconnection time when its value is valid. An `id:` field updates the last-event-ID string; on reconnect, a nonempty value is sent in the `Last-Event-ID` request header. HTTP 204 tells the client not to reconnect. This mechanism provides a cursor for resumption, but does not itself guarantee that the server retains or replays events, nor does it guarantee exactly-once delivery.
  Source: [HTML Standard — Server-sent events](https://html.spec.whatwg.org/multipage/server-sent-events.html)

- **LLM streaming implications:** SSE is suitable for incrementally delivering textual generation chunks and structured control events over a long-lived response. A server can encode each chunk as `data:` (often JSON), use named events for lifecycle/error signals, and terminate the stream with an application-defined completion event. The browser dispatches only complete events after the blank-line delimiter, so servers should flush complete event frames promptly; partial lines or frames are not yet dispatched. If reconnect/resume is desired, the application must define stable IDs and server-side replay semantics; otherwise a reconnect can duplicate or omit generated content. Native `EventSource`’s lack of arbitrary headers/body is a practical constraint for LLM APIs that require POST prompts or bearer-token headers. These are engineering implications derived from the standard, not requirements imposed by it.
  Source: [HTML Standard — Server-sent events](https://html.spec.whatwg.org/multipage/server-sent-events.html)

## Evidence and uncertainty
The primary evidence is the assigned WHATWG HTML Living Standard page, which documents the interface, request construction, processing model, and event-stream parsing rules. The fetched page was truncated after substantial relevant content; the findings above rely on the returned text and the standard’s identified sections. The standard specifies browser behavior but does not prescribe LLM-specific chunk schemas, token boundaries, replay storage, or exactly-once semantics. Those depend on application and server design. No independent second primary source was verified in this run.

## References
- [HTML Standard — Server-sent events](https://html.spec.whatwg.org/multipage/server-sent-events.html)