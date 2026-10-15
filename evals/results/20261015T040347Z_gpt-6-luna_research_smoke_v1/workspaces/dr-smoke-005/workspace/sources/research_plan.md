# Research Plan

## Research question
Compare local/on-device and cloud-hosted ASR/TTS architectures for a real-time voice agent across privacy, latency, deployment complexity, model quality, scalability, and operating cost. Recommend a small-prototype architecture and a production-service architecture.

## Evidence approach
Prioritize primary documentation and technical papers from model/framework providers and standards bodies. Distinguish architectural facts from context-dependent estimates. Cite only exact URLs returned by this run's web search or successful fetch. Count distinct page URLs (not fragments) preserved in findings before analysis/drafting; target at least five.

## Focused researcher assignments and distinct target pages
1. Local/on-device speech recognition and synthesis: model/runtime capabilities, offline/privacy implications, and device constraints. Target source page: https://github.com/ggerganov/whisper.cpp (Whisper.cpp project documentation). Output: `/workspace/sources/findings_local_asr.md`.
2. Cloud speech APIs and service architecture: streaming interfaces, deployment/operational characteristics, and provider-side capabilities. Target source page: https://cloud.google.com/speech-to-text/docs/streaming-recognize (Google Cloud Speech-to-Text streaming recognition documentation). Output: `/workspace/sources/findings_cloud_asr.md`.
3. Real-time voice-agent latency and end-to-end architecture: streaming TTS/ASR, turn-taking, and latency-sensitive design. Target source page: https://platform.openai.com/docs/guides/text-to-speech (OpenAI text-to-speech guide). Output: `/workspace/sources/findings_realtime_tts.md`.

Additional distinct primary source pages to verify/preserve if needed for the five-page minimum and cost/quality evidence:
- https://platform.openai.com/docs/guides/speech-to-text (OpenAI speech-to-text guide)
- https://cloud.google.com/text-to-speech/docs/streaming (Google Cloud Text-to-Speech streaming documentation)
- https://github.com/rhasspy/piper (Piper local neural TTS project)
- https://arxiv.org/abs/2212.04356 (Whisper paper)

## Analysis and deliverables
After findings are complete, count distinct source pages preserved in findings. If fewer than five, use remaining search/research budget to add a new focused findings file with a distinct source page. Then delegate one analyst to compare trade-offs and uncertainty, writing `/workspace/sources/analysis_local_cloud_voice.md`. Draft in English at `/workspace/reports/draft_local_cloud_voice.md`, obtain one editor review, revise once, and save final report to `/workspace/reports/report_local_cloud_voice_2026-10-14.md`.