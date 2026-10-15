# Local vs. Cloud ASR/TTS Architectures for a Real-Time Voice Agent

## Background

A real-time voice agent typically captures speech, detects turns, recognizes speech (ASR), generates a response, synthesizes speech (TTS), and plays audio back. The architecture can run speech models on the user's device, call managed cloud services, or combine both. The choice affects where audio is processed, how quickly results arrive, what engineering and operations are required, and how costs scale.

The evidence reviewed here includes local inference/runtime documentation, platform API documentation, and cloud streaming ASR/TTS documentation. It supports architectural comparisons, but not a universal performance or cost winner.

## Key Findings

- **Local processing offers a path to data locality and offline operation, not an automatic privacy guarantee.** Local inference can keep audio and transcripts on-device, but logs, crash reports, backups, analytics, model downloads, and synchronization must also be considered. The `whisper.cpp` project documents local inference and multiple hardware acceleration paths; Android's `SpeechRecognizer` API illustrates that platform recognizer availability and offline behavior need explicit verification.
- **Streaming is central to perceived responsiveness in either architecture.** Google Cloud Speech-to-Text documents incremental streaming recognition. OpenAI's TTS and Realtime guides describe streaming output and interactive voice patterns. Streaming can overlap processing and playback, but network, buffering, turn detection, and model generation still contribute to end-to-end latency.
- **Cloud services reduce the need to operate inference hardware but add integration and service dependencies.** The documented Google streaming path requires a billed project, API enablement, IAM/authentication, a bidirectional gRPC stream, and audio chunking within a 25 KB per-message limit.
- **The evidence does not establish comparative model quality, numerical latency, or cost superiority.** No controlled local-versus-cloud benchmark was found in the reviewed material. The cloud pricing page did not provide usable rate details in the retrieved content, and no specific local TTS implementation was substantiated.

## Evidence and Analysis

### Privacy

Local ASR can avoid sending captured audio to a remote inference service, assuming the model is already available and the application does not transmit audio or transcripts through other channels. A privacy review should cover the full data flow, including telemetry, crash reporting, backups, model acquisition, and updates. Cloud ASR necessarily sends audio to a provider for processing; the reviewed cloud findings do not establish provider retention or processing terms. Therefore, privacy decisions require both application-level data-flow review and current provider terms, not just a “local” or “cloud” label.

### Latency and interaction design

Local inference avoids network round trips but may still be slow on constrained devices, especially with larger models, thermal throttling, or inefficient segmentation. Cloud streaming can return partial recognition results while audio is being processed, but network and service delays remain. Streaming TTS can allow playback to begin before the full response is synthesized. In both cases, perceived latency depends on the whole pipeline: capture, endpoint/turn detection, ASR, response generation, TTS, transport, buffering, and playback. Barge-in and interruption handling also matter: conservative turn-end detection delays responses, while aggressive detection risks cutting off the user.

### Deployment, quality, scale, and cost

Local deployment shifts work to model packaging/distribution, runtime and hardware compatibility, memory/storage/energy management, and device-specific testing. Cloud deployment shifts work to credentials, API integration, connectivity, quotas, and service operations. The reviewed cloud guide documents a 25 KB per-message audio limit for streaming requests; other production limits and service guarantees were not established in the findings.

Neither architecture can be assumed to provide better recognition accuracy or more natural speech without representative evaluation. Local quality depends on model, language, acoustic conditions, quantization, and runtime. The cloud evidence establishes streaming interfaces, not comparative accuracy. Likewise, the available evidence does not support a numerical cost comparison: local costs include engineering and device/model distribution considerations, while cloud costs depend on usage and configuration, but current rates and workload assumptions are missing.

## Comparison

| Dimension | Local/on-device | Cloud-hosted | Practical implication |
|---|---|---|---|
| Privacy | Can keep inference data on-device and support offline use; other app data flows can still leak information. | Audio is sent to a provider; retention and processing terms must be checked. | Prefer local when data locality/offline operation is a hard requirement; audit the complete data path either way. |
| Latency | No network round trip, but constrained hardware and model/runtime choices can limit speed. | Streaming can return incremental results, but network and service delays remain. | Benchmark time-to-first-result/audio and full-turn latency under realistic conditions. |
| Deployment complexity | Model/runtime packaging, device compatibility, updates, and resource/thermal testing. | API setup, authentication, streaming transport, chunking, connectivity, and quota management. | Local complexity is client/device-centric; cloud complexity is integration/operations-centric. |
| Model quality | Depends on model, language, acoustics, quantization, and device. | Depends on provider/model/configuration; reviewed sources do not establish a quality advantage. | Evaluate ASR error and TTS naturalness on representative users and environments. |
| Scalability | Compute is distributed across devices; fleet diversity and support burden grow. | Managed inference can centralize serving, subject to quotas, regions, and service limits. | Verify concurrency and service limits for cloud; validate device coverage for local. |
| Operating cost | No direct per-request rate is established; engineering, distribution, and device resource costs remain. | Usage-based costs may apply, but the reviewed pricing evidence is insufficient for a rate estimate. | Build a workload-specific cost model using current prices and measured usage; do not assume either is cheaper. |

## Recommendations

### Small prototype

For a prototype whose main goal is to validate conversational behavior quickly, start with a **cloud streaming ASR/TTS path** if connectivity and sending audio to a provider are acceptable. Managed inference avoids first building a local model distribution and optimization stack. Keep the prototype narrow: implement streaming, authentication, chunking, turn detection, and interruption handling, then measure time-to-first-result/audio and full-turn latency.

Choose **local ASR** instead when offline operation or keeping audio on-device is a core requirement and the target device is known. Test the selected model/runtime on representative hardware; local execution alone does not guarantee real-time performance. The reviewed evidence does not support a specific local TTS engine, so local TTS should be selected only after separate quality and performance evaluation.

### Production service

Use a **requirements-led architecture**, not a presumed universal winner. A cloud-first service is a reasonable default when managed inference and centralized operations are priorities and provider processing is acceptable. A local-first or hybrid design is more appropriate when offline operation, strict data locality, or resilience to network loss is mandatory. Hybrid routing can preserve local operation for selected cases while using cloud services where appropriate, but it adds routing, fallback, consistency, and testing complexity.

Before production commitment:

1. Run end-to-end tests across target devices, languages, accents, noise conditions, network conditions, and expected concurrency.
2. Measure ASR quality, TTS naturalness, time-to-first-result/audio, full-turn latency, resource use, and failure/recovery behavior.
3. Verify current cloud pricing, quotas, stream-duration limits, regional availability, retry behavior, and service guarantees; validate local model distribution, updates, thermal behavior, and all non-inference data egress paths.
4. Document retention, consent, and data-flow decisions, and calculate cost from expected workload rather than generic assumptions.

## Limitations

The evidence is asymmetric: local findings focus on `whisper.cpp` and an Android API boundary; cloud ASR findings focus on Google Cloud; TTS findings describe streaming patterns but do not provide a controlled local-versus-cloud comparison. No comparable benchmark establishes accuracy, latency, throughput, or resource use. The reviewed cloud pricing page did not yield usable rate details, and quotas, concurrency limits, stream duration, regional latency, and service guarantees remain unverified. No specific local TTS implementation was substantiated. Provider data retention terms, target hardware, workload volume, language mix, concurrency, privacy requirements, and budget were not supplied. Conclusions should therefore be treated as architectural guidance, not a quantified performance or cost forecast.

### References (official documentation and project sources)

1. [whisper.cpp — high-performance inference of OpenAI's Whisper ASR model](https://github.com/ggml-org/whisper.cpp)
2. [Android `SpeechRecognizer` API reference](https://developer.android.com/reference/android/speech/SpeechRecognizer)
3. [Transcribe audio from streaming input — Google Cloud Speech-to-Text](https://docs.cloud.google.com/speech-to-text/docs/streaming-recognize)
4. [Speech-to-Text API Pricing — Google Cloud](https://cloud.google.com/speech-to-text/pricing)
5. [Text to speech — OpenAI API](https://developers.openai.com/api/docs/guides/text-to-speech)
6. [Getting started with the Realtime API — OpenAI API](https://developers.openai.com/api/docs/guides/realtime)

The six references above are six distinct source pages preserved in the in-run findings. The pricing page is included as a source for the documented pricing reference, not as evidence of a specific rate. The comparison of local and cloud scalability, privacy implications, and deployment burden is architectural reasoning based on the described data paths and integration requirements; the cited sources do not provide a controlled cross-architecture evaluation. Cloud processing entails sending audio to the selected provider for processing, but retention and subsequent handling depend on provider terms not established here. No local TTS implementation or local-versus-cloud TTS benchmark was substantiated.