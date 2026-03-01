# SermonPlan.md — PSR: Pastor Sermon Rating

## Vision

A public web platform where anyone can upload sermon audio and receive a data-driven **Pastor Sermon Rating (PSR)** — like a QBR for quarterbacks, but for preachers. Upload a sermon, get a score, see the breakdown.

Built on Azure to showcase its AI, serverless, and data platform capabilities.

---

## The PSR Score (0-100 Composite)

### Categories (Weighted)

| Category | Weight | What It Measures |
|----------|--------|-----------------|
| **Biblical Accuracy** | 25% | Scripture references detected, verified against passage context. Flags controversial interpretations rather than marking wrong. |
| **Time in the Word** | 20% | Percentage of sermon spent in scripture/biblical content vs anecdotes, illustrations, stories. |
| **Passage Focus** | 10% | Time spent on the main/announced passage vs tangents. |
| **Clarity** | 10% | Logical structure, flow between points, clear transitions. |
| **Engagement** | 10% | Energy level, pacing variation, audience connection cues. |
| **Application** | 10% | Practical takeaways, actionable points, real-world relevance. |
| **Delivery** | 10% | Filler words, confidence, articulation. |
| **Emotional Range** | 5% | Tone variation, passion, authenticity via sentiment arc and vocal prosody. |

> **⚠️ Confirmed bias (POC #4):** Sermon type dramatically affects scoring. Same preacher, 3-4x scripture density gap between expository and topical sermons. **Decision: normalize within sermon type.** Tag each sermon as expository/topical/survey and score against peers of the same type. See [docs/research.md](docs/research.md) for full POC #4 results.

### Design Principle

Biblical Accuracy measures whether the pastor *correctly handles the text they reference* — not whether their theology is "right." A Calvinist and an Arminian preaching Romans 9 can both score 90+ if they accurately represent what the text says. The score penalizes misquoting, out-of-context proof-texting, and factual errors — not denominational convictions.

### Scholarly Verification Engine (Phase 1)

For MVP, Biblical Accuracy uses Azure OpenAI's built-in Bible knowledge. Phase 1 adds a three-layer RAG approach:

1. **Curated Theological Database** — Bible text corpus (ESV, NIV, KJV, NASB), cross-reference tables
2. **Commentary Corpus** — Indexed by theological tradition (Reformed, Wesleyan, Baptist, Evangelical, Academic) to avoid scoring bias
3. **AI Cross-Reference** — Flags claims as ✅ Aligned, ⚠️ Debated (no penalty), or ❌ Contradicts (factual errors only)

---

## MVP Scope — Phase 0: "Does This Thing Work?"

The goal: **upload a sermon, get a score, see the results.** Nothing else.

### In Scope
- Upload audio file (MP3, WAV, M4A — no video)
- No auth — skip Azure AD B2C, just get the pipeline working
- Transcription via Azure AI Speech (with timestamps)
- Segment classification via Azure OpenAI (scripture, teaching, anecdote, application, etc.)
- Scripture detection and verification against Bible text (GPT-4's built-in knowledge)
- PSR scoring — all 8 categories + composite
- Parselmouth for audio-level metrics (pitch, volume, pauses) — proven in POC #3, feeds pre-computed data to GPT-4. **Only** open-source analysis tool in MVP (textstat and spaCy dropped — POC #4 showed nonsensical results on whisper transcripts)
- GPT-4 for all text analysis — POC #4 confirmed LLM is significantly more accurate than NLP heuristics. POC #5 confirmed Azure AI Speech transcription quality is superior to local Whisper for scripture detection (correctly parses "Romans 8:28" vs Whisper's "Romans 828")
- Simple web UI (Next.js on Static Web Apps): upload page, sermon feed, sermon detail with scorecard + transcript
- Processing status indicator while sermon is being analyzed
- English only, max 1 hour

### Open Decisions
- [ ] Scoring calibration strategy — normalization curves are hardcoded estimates (topical +5/+8/+10 for biblical categories). After 20-30 scored sermons across types, revisit with real data. POC #7 baseline: Piper expository = 88.0 composite.
- [ ] Cost monitoring / budget alerts on Azure before deploying — $100/mo budget set (see AZURE_SETUP.md), need to verify alerts fire
- [ ] Cosmos DB serverless vs simpler alternatives (friend to confirm)

### ⚠️ Known Issues (from POC #5)
- **Transcription word loss:** Azure AI Speech real-time chunking (5-min ffmpeg splits) dropped ~72% of words on a 35-min sermon (1,064 vs 3,794 expected). **Fixed in POC #6:** Fast transcription API recovered 99.2% of words (3,762 vs 3,794). Synchronous, no blob storage needed, 47x faster than real-time. Add WPM sanity check (flag if < 80 or > 200).
- **Scoring on partial transcript:** POC #5 scored on the 1,064-word partial transcript. **POC #7 re-scored on the full 3,762-word transcript:** composite jumped 82.7 → 88.0 (+5.3). Application +13, Clarity +10, Delivery +10. Scripture refs: 12 vs 6. **Lesson: always score on complete transcripts.** Pipeline architecture already enforces this (transcribe → score).
- **Filler word blindness:** Both Whisper and Azure Speech skip disfluencies (um, uh). POC #5 reported 0 fillers. CrisperWhisper remains the only known solution but adds complexity. **Decision for MVP:** Accept filler undercounting — delivery score relies more on Parselmouth audio metrics (pauses, pitch) than filler counts. Revisit in Phase 1.

### NOT in MVP
- Video upload / transcoding
- Auth, user accounts, social login
- Pastor profiles, claiming, opt-out
- Leaderboards, search, follow/playlists
- Content moderation
- Commentary corpus RAG
- 2-hour sermon support

### MVP Azure Services

| Service | Purpose |
|---------|---------|
| **Static Web Apps** | Next.js frontend (free tier) |
| **Azure Functions** | API + processing logic (consumption plan) |
| **Durable Functions** | Pipeline orchestration |
| **Blob Storage** | Store uploaded audio files |
| **AI Speech Service** | Transcription with timestamps |
| **Azure OpenAI** | Multi-model: o4-mini (biblical reasoning), GPT-4.1 (structure eval), GPT-4.1-mini (delivery eval), GPT-4.1-nano (classification). See [research](docs/research.md#azure-openai-model-selection-research-july-2025) |
| **Cosmos DB** | Sermon metadata + results (serverless tier) |
| **Key Vault** | Secrets |

### MVP Estimated Cost
~$20-50/mo during development (5 free Speech hours/mo covers ~7 sermons). **~$0.75 per sermon** with fast transcription + multi-model strategy: $0.67 speech + $0.09 OpenAI (3 parallel passes on ~5K-7K word transcripts). Batch API alternative: ~$0.33/sermon if latency isn't critical. See [cost analysis](docs/research.md#cost-analysis-all-poc-runs).

---

## MVP Pipeline

```
Upload audio file
    │
    ▼
1. Azure Function: validate file, create sermon record in Cosmos DB (status: processing)
    │
    ▼
2. Store in Blob Storage
    │
    ▼
3. Durable Function Orchestrator:
    │
    ├─► Transcribe (Azure AI Speech fast transcription API — timestamps + diarization)
    │     Synchronous, handles up to 2hr/300MB natively. No blob storage needed.
    │     POC #6: 3,762 words in 44s for 35-min sermon. $1.00/hr.
    ├─► Audio analysis (Parselmouth — pitch, volume, pauses)
    │
    │   ── 3 parallel scoring passes (fan-out) ──
    │
    ├─► Pass 1: Biblical Analysis — o4-mini ($1.10/$4.40 per 1M tokens)
    │     Categories: Biblical Accuracy, Time in the Word, Passage Focus
    │     Why o4-mini: scripture verification needs chain-of-thought reasoning
    │     ("is this quote used in context?") — reasoning model required
    │
    ├─► Pass 2: Structure & Content — GPT-4.1 ($2.00/$8.00 per 1M tokens)
    │     Categories: Clarity, Application, Engagement
    │     Why GPT-4.1: rubric-following + structured JSON output — best
    │     instruction-following model, no deep reasoning needed
    │
    ├─► Pass 3: Delivery — GPT-4.1-mini ($0.40/$1.60 per 1M tokens)
    │     Categories: Delivery, Emotional Range
    │     Why GPT-4.1-mini: interprets pre-computed Parselmouth data
    │     (pitch, pauses, volume) — heavy lifting already done, cheapest
    │     model with reliable structured output
    │
    │   ── fan-in ──
    │
    ├─► Sermon type classification + metadata extraction — GPT-4.1-mini
    │     Classification: expository / topical / survey
    │     Metadata: sermon title, pastor name, main passage (if not provided by uploader)
    │
    ├─► Segment classification — GPT-4.1-mini
    │     Label transcript segments: scripture / teaching / application /
    │     anecdote / illustration / prayer / transition
    │     Required for frontend transcript viewer color-coding
    │
    ├─► Score normalization — pure code (no LLM)
    │     Adjust raw scores by sermon type using normalization curves
    │
    └─► Store results in Cosmos DB, update status to complete
```

**~$0.75 per sermon** ($0.67 speech + $0.09 OpenAI). See [cost analysis](docs/research.md#cost-analysis-all-poc-runs) for full breakdown.

---

## Next Steps

### Phase 0 — MVP (Current Target)
1. Set up Azure resource group + Bicep templates for minimal services
2. Build upload → transcribe → store pipeline (Durable Functions orchestration)
3. Build PSR scoring engine with Azure OpenAI (all 8 categories)
4. Build frontend: upload page + sermon detail page with scorecard, transcript, segment timeline, processing status
5. Deploy to dev environment, test with real sermons

### Phase 1 — Public Launch
- Auth (Azure AD B2C)
- Video upload support (Media Services)
- Commentary corpus RAG for Biblical Accuracy
- Pastor profiles, claiming, opt-out
- Leaderboards and search
- Content moderation
- 2-hour sermon support

### Phase 2 — Growth
- Semantic/vector search
- Follow pastors, playlists
- Video-specific analysis
- Multi-language support
- Church organization accounts
- Sermon comparison (side-by-side)
- API for third-party integrations

---

## Related Docs

- **[docs/architecture.md](docs/architecture.md)** — Full platform architecture, data model, cost estimates, AWS comparison
- **[docs/research.md](docs/research.md)** — Competitive landscape, POC results (#1-4), open-source tools evaluation, data sources
- **[docs/team.md](docs/team.md)** — Who's building this, dev tooling, setup checklists
