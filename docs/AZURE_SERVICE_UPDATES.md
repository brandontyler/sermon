# Azure Service Updates

Changes and clarifications since the architecture docs were written that affect PSR.

Last verified: 2026-03-01 (via `az cognitiveservices account deployment list`)

## Current Model Deployments (Verified Working)

| Deployment Name | Model | Version | PSR Role |
|----------------|-------|---------|----------|
| `o4-mini` | o4-mini | 2025-04-16 | Pass 1: Biblical Analysis (reasoning) |
| `gpt-41` | gpt-4.1 | 2025-04-14 | Pass 2: Structure & Content |
| `gpt-41-mini` | gpt-4.1-mini | 2025-04-14 | Pass 3: Delivery + Classification |
| `gpt-4o` | gpt-4o | 2024-11-20 | Legacy (used in early POCs, no longer needed) |

All models confirmed working in POC #5 and POC #7. No changes needed for MVP.

## Branding: "Azure OpenAI" → "Microsoft Foundry"

The branding chain: Cognitive Services → Azure AI Services → Azure AI Foundry → **Microsoft Foundry**.

The resource provider is still `Microsoft.CognitiveServices` and CLI commands still work. The portal and model catalog are now at [ai.azure.com](https://ai.azure.com) under the Foundry brand. This is cosmetic — no code changes needed.

## Azure Cache for Redis → Azure Managed Redis

Azure Cache for Redis is retiring (Enterprise: March 2027, Basic/Standard/Premium: Sept 2028). New projects should use **Azure Managed Redis**. This affects Phase 2 leaderboard caching only — not MVP.

## Azure Media Services — Retired June 2024

No first-party Azure replacement for video transcoding. We registered `Microsoft.VideoIndexer` for Phase 1 video analysis. For transcoding: FFmpeg on Functions or third-party. MVP is audio-only, not blocked.

## Static Web Apps Dedicated Plan — Retired

The paid "Dedicated" plan was retired. Free tier still works and is what we use for MVP. No impact.

## Worth Evaluating (Phase 1)

### gpt-4o-transcribe-diarize Model

Azure now offers a GPT-4o-based transcription model with built-in speaker diarization, available in Foundry. Could potentially replace Azure AI Speech, simplifying to a single service. Trade-offs to evaluate:
- Cost comparison vs AI Speech ($1/hr)
- Accuracy on sermon audio (single speaker, variable recording quality)
- Timestamp granularity (word-level needed for segment timeline)

Not needed for MVP — Azure AI Speech fast transcription is proven (POC #6, #7).

### GPT-5 Series Models

GPT-5, GPT-5-mini, and GPT-5-nano are available on Azure but require quota approval. Bead `sermon-1q2` tracks the quota request. Current models are solid — this is a cost optimization, not a blocker.

## Action Items

- [x] ~~Verify model availability~~ — confirmed 2026-03-01, all models working
- [ ] Evaluate gpt-4o-transcribe-diarize vs Azure AI Speech (Phase 1)
- [ ] Request GPT-5 series quota when ready for cost optimization (bead sermon-1q2)
