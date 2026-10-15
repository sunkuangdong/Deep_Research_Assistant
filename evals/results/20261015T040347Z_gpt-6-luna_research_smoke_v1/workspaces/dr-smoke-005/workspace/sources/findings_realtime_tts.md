# Findings: Real-Time TTS and Voice-Agent Latency Architecture

## Scope
This file covers real-time text-to-speech streaming and end-to-end voice-agent latency architecture, including how incremental synthesis and turn-taking affect perceived responsiveness, plus cloud-versus-local deployment tradeoffs. It does not assess unrelated voice-agent topics. The requested TTS page was fetched; the fetch resolved to the current OpenAI documentation URL recorded below.

## Key Findings
- OpenAI's TTS guide describes speech generation through the Audio API and supports streaming audio output, allowing playback to begin before the full response has been synthesized. This can reduce perceived response latency, although it does not by itself eliminate upstream model-generation, network, buffering, or playback delays.
  Source: [Text to speech | OpenAI API](https://developers.openai.com/api/docs/guides/text-to-speech)
- For an end-to-end voice agent, latency is a pipeline property: input capture and transport, turn-end detection, model response generation, audio synthesis, and output transport/playback all contribute. A streaming design can overlap response generation and speech playback rather than waiting for a complete text response and complete audio file.
  Source: [Getting started with the Realtime API | OpenAI API](https://developers.openai.com/api/docs/guides/realtime)
- Turn-taking is coupled to latency. Waiting for a long silence or a conservative end-of-turn decision delays the start of the response; overly eager turn completion risks interrupting the user or responding to an incomplete utterance. In interactive systems, interruption/barge-in handling and the ability to stop or replace ongoing output are therefore part of the latency architecture, not merely UI details.
  Source: [Getting started with the Realtime API | OpenAI API](https://developers.openai.com/api/docs/guides/realtime)
- Cloud synthesis offers managed model serving and avoids requiring a capable local inference stack, but introduces network round-trip and service-dependency costs. Local synthesis can avoid a cloud round trip and may improve privacy or offline operation, but latency and quality depend on local hardware, model size, runtime optimization, and resource contention. These are architectural tradeoffs; the cited OpenAI pages do not provide a controlled cloud-versus-local benchmark.
  Source: [Text to speech | OpenAI API](https://developers.openai.com/api/docs/guides/text-to-speech)

## Evidence and Uncertainty
The official documentation supports the availability of streaming TTS and realtime voice interaction patterns, but does not establish universal latency figures or a quantitative cloud/local comparison. Actual time-to-first-audio and conversational latency vary with network conditions, model choice, response length, buffering, turn-detection settings, and client playback. The requested URL redirected during retrieval to the exact fetched URL cited here. The additional primary source is OpenAI's Realtime API guide. No independent benchmark was used, so deployment tradeoffs should be validated under the target workload and network conditions.

## Reference Sources
- [Text to speech | OpenAI API](https://developers.openai.com/api/docs/guides/text-to-speech)
- [Getting started with the Realtime API | OpenAI API](https://developers.openai.com/api/docs/guides/realtime)
