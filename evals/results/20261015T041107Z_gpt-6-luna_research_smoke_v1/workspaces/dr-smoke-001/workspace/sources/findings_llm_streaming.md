# Findings: LLM streaming implementation patterns for browser-based AI assistants

## Research scope
This note covers OpenAI Responses API streaming patterns relevant to rendering assistant output in a browser-based product, and the transport implications directly supported by the assigned guide. It does not attempt a general SSE-versus-WebSocket comparison. The assigned legacy URL redirected on successful retrieval; citations use only the exact verified `Fetched URL:` values.

## Key findings
- **Documented — HTTP streaming is the guide’s default pattern.** OpenAI describes `stream=true` on the Responses endpoint as HTTP streaming over server-sent events (SSE). Its examples consume a stream incrementally (`for await ... of stream` in JavaScript) rather than waiting for a complete response. This supports progressively displaying or processing output as it is generated.
  Source: [Streaming API responses | OpenAI API](https://developers.openai.com/api/docs/guides/streaming-responses.md)

- **Documented — events are semantic and typed, not just text chunks.** The guide says each event has a predefined schema and can be selected by its `type`. It identifies `response.created`, repeated `response.output_text.delta`, `response.completed`, and `error` as common text-stream events. Its example appends each text delta, handles completion separately, and reports errors. The event union also includes lifecycle, output-item/content-part, refusal, function-call-argument, and tool-progress events.
  Source: [Streaming API responses | OpenAI API](https://developers.openai.com/api/docs/guides/streaming-responses.md)

- **Implementation implication — model the UI as an event-driven state machine.** A browser assistant should distinguish response lifecycle from user-visible text: initialize/mark a response on creation, append text deltas, and finalize on completion; handle errors explicitly. This is an inference from the documented event types and examples, not a prescribed UI architecture.
  Evidence: [Streaming API responses | OpenAI API](https://developers.openai.com/api/docs/guides/streaming-responses.md)

- **Transport implication — for a one-way generated response, the documented HTTP/SSE stream is a natural fit.** The guide explicitly presents HTTP streaming over SSE for `stream=true`; therefore, when the browser interaction is a request followed by incremental server-to-client output, this is the directly documented pattern. This is an implementation inference, not a claim that SSE is universally preferable or that the guide specifies browser authentication/proxy details.
  Evidence: [Streaming API responses | OpenAI API](https://developers.openai.com/api/docs/guides/streaming-responses.md)

- **Documented alternative — WebSocket mode is positioned for persistent transport and incremental inputs.** The streaming guide points to Responses API WebSocket mode for persistent WebSocket transport with incremental inputs via `previous_response_id`. This suggests considering that mode when the interaction requires ongoing input updates over a persistent connection; the guide does not say ordinary text streaming requires WebSockets.
  Source: [Streaming API responses | OpenAI API](https://developers.openai.com/api/docs/guides/streaming-responses.md)

- **Documented — streaming complicates moderation.** OpenAI warns that partial completions are harder to moderate, and says moderation scores requested with a generation request arrive only after the full output is available, not with partial deltas. A browser UI that reveals deltas immediately therefore has a moderation-timing tradeoff; that product implication is an inference from the stated limitation.
  Source: [Streaming API responses | OpenAI API](https://developers.openai.com/api/docs/guides/streaming-responses.md)

## Evidence and uncertainty
The primary guide was successfully fetched in Markdown and provides direct evidence for the transport description, event names/types, SDK iteration pattern, WebSocket pointer, and moderation caveat. The original requested `platform.openai.com` URL was not returned as a verified URL; the successful fetch resolved to the developers.openai.com Markdown page, which is the cited URL. The guide does not specify browser-side connection setup, credential handling, reconnection, buffering, cancellation, or rendering strategy. Recommendations about UI state handling and when to choose a transport are explicitly labeled as inferences. Search results did not provide a useful official result, so no non-primary sources are used.

## References
- [Streaming API responses | OpenAI API](https://developers.openai.com/api/docs/guides/streaming-responses.md)
