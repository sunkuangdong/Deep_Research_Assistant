# Findings: Cloud-hosted ASR architecture for real-time voice agents

## Scope
This note covers cloud-hosted streaming speech recognition interfaces and documented operational, deployment, scaling, and cost considerations, using Google Cloud Speech-to-Text streaming recognition as the focal example. It excludes local model runtimes and does not generalize beyond the cited provider documentation.

## Key findings
- Google Cloud Speech-to-Text streaming recognition accepts audio incrementally and returns recognition results as the audio is processed, making it a cloud API pattern suitable for real-time transcription in a voice-agent pipeline. The documented streaming interface is gRPC-only; it is not presented as a REST streaming interface.
  Source: [Transcribe audio from streaming input](https://docs.cloud.google.com/speech-to-text/docs/streaming-recognize)
- The streaming request has a 25 KB limit on audio in each request message, including the initial `StreamingRecognize` request. A client therefore needs to chunk audio within that bound and maintain a bidirectional streaming connection. The documentation's example uses a client library and a generator of audio chunks; it also notes that the example reads a local file, which is illustrative rather than a deployment requirement.
  Source: [Transcribe audio from streaming input](https://docs.cloud.google.com/speech-to-text/docs/streaming-recognize)
- Operational setup includes a billed Google Cloud project, enabling the Speech-to-Text API, IAM permissions, and client authentication. The documentation describes Application Default Credentials as a way to use the same client authentication approach locally and after deployment, avoiding code changes between those environments.
  Source: [Transcribe audio from streaming input](https://docs.cloud.google.com/speech-to-text/docs/streaming-recognize)
- The pricing page is the provider's primary reference for service charges, but the retrieved page output contained only its title and no pricing details. Consequently, this research cannot substantiate a per-minute rate, free tier, model-specific price, or a cost comparison. For a real-time agent, usage-based audio volume and selected model/configuration are cost variables to verify against the current pricing page before estimating spend.
  Source: [Speech-to-Text API Pricing](https://cloud.google.com/speech-to-text/pricing)

## Evidence and uncertainty
The streaming interface and its 25 KB per-message constraint are directly stated in the streaming guide. The guide also points readers to separate audio limits, quotas, and best-practices documentation, but those pages were not retrieved here; concurrent-stream quotas, maximum stream duration, regional availability/latency, retry behavior, and service-level guarantees are therefore not established in this note. The pricing page was successfully fetched, but its returned content was truncated to the title, so no numerical cost claims are supported. Findings are specific to the cited Google Cloud documentation and should not be treated as a survey of cloud ASR providers.

## Reference sources
- [Transcribe audio from streaming input](https://docs.cloud.google.com/speech-to-text/docs/streaming-recognize)
- [Speech-to-Text API Pricing](https://cloud.google.com/speech-to-text/pricing)
