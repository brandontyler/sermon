# Agent Instructions

## Project Overview

PSR (Pastor Sermon Rating) — A public web platform where anyone can upload sermon audio and receive a data-driven score (0-100 composite), like a QBR for quarterbacks but for preachers. Built on Azure serverless + AI services.

**Current Phase:** MVP (Phase 0) — "Does This Thing Work?"
Upload a sermon → get a score → see the breakdown. Nothing else.

## PSR Score (0-100 Composite)

| Category | Weight | What It Measures |
|----------|--------|-----------------|
| Biblical Accuracy | 25% | Scripture references verified against passage context. Flags controversial interpretations, doesn't mark wrong. |
| Time in the Word | 20% | Biblical content density (quoted + taught + applied + exposited), not just direct quotation %. |
| Passage Focus | 10% | Time on main passage vs tangents. |
| Clarity | 10% | Logical structure, flow, transitions. |
| Engagement | 10% | Energy, pacing variation, audience connection. |
| Application | 10% | Practical takeaways, actionable points. |
| Delivery | 10% | Filler words, confidence, articulation. |
| Emotional Range | 5% | Tone variation, passion, authenticity. |

Scores normalize within sermon type (expository/topical/survey). Tiered confidence: <80% → no normalization, 80-90% → half bump, >90% → full bump.

Biblical Accuracy is denomination-neutral — penalizes misquoting and proof-texting, not theological convictions.

## Pipeline (high level)

```
Upload → Validate + Cosmos record → Blob Storage →
  Wave 1 (parallel): Transcribe (AI Speech fast API) + Parselmouth audio analysis →
  Wave 2 (throttle-aware parallel): 6 LLM passes →
    Pass 1: Biblical Analysis (o4-mini) — biblicalAccuracy, timeInTheWord, passageFocus
    Pass 2: Structure & Content (gpt-5-mini) — clarity, application, engagement
    Pass 3: Delivery (gpt-5-nano) — delivery, emotionalRange
    Classify: sermon type + metadata (gpt-5-nano)
    Segments: transcript segment labels (gpt-5-nano)
    Pass 4: Enrichment (gpt-5-nano) — biblical languages, church history
  Fan-in → Score normalization (pure code) → Summary (gpt-5-nano) → Store in Cosmos
```

~$0.75/sermon ($0.67 speech + $0.09 OpenAI).

## Tech Stack (MVP)

| Layer | Tech |
|-------|------|
| Frontend | Next.js on Azure Static Web Apps |
| API + Processing | Azure Functions (consumption plan) |
| Orchestration | Durable Functions |
| Storage | Blob Storage (audio), Cosmos DB serverless (metadata + results) |
| Transcription | Azure AI Speech (fast transcription API) |
| Analysis | Azure OpenAI multi-model (o4-mini, gpt-5-mini, gpt-5-nano) |
| Audio Metrics | Parselmouth (pitch, volume, pauses) |
| Secrets | Azure Key Vault |

## MVP Boundaries

In: audio upload (MP3/WAV/M4A), text upload, transcription, 8-category scoring, segment classification, enrichment, simple web UI, English only, max 1 hour.

Not in: video, auth, pastor profiles, leaderboards, search, content moderation, commentary RAG, 2-hour support.

## Key Docs

| Doc | Purpose |
|-----|---------|
| `sermonplan.md` | Full vision, detailed pipeline, POC history, all known issues, future phases |
| `docs/architecture.md` | Platform architecture, data model, cost estimates |
| `docs/research.md` | Competitive landscape, POC results, tools evaluation, model selection |
| `docs/rescore.md` | Detailed rescore operations reference (selective, staleness, workflows) |
| `docs/team.md` | Who's building this, dev tooling, setup |

## Issue Tracking (Beads)

Uses **br** (beads-rust) — git-native task tracker in `.beads/`.

| Command | Purpose |
|---------|---------|
| `br ready` | Find work with no blockers (START HERE) |
| `br list` | List all issues |
| `br show <id>` | View details + blockers |
| `br update <id> --claim` | Claim work |
| `br close <id> --reason "..."` | Complete work |
| `br create "Title" -p 1 -t task` | Create task (P0-P3) |
| `br sync --flush-only` | Export DB → JSONL (then git add + commit) |
| `br sync --import-only` | Import JSONL → DB (after git pull) |

Workflow: `br ready` → claim → work → close → flush. Create issues for discovered work, don't leave TODOs in code.

## Cost Controls

- **NEVER kick off a full rescore (`POST /api/rescore {"all": true}`) without asking Brandon or Orlando first.** ~$1.50, ~90 minutes. Propose, explain, wait for approval.
- Single-sermon and selective rescores are fine without asking.
- Same rule for any bulk Azure operation with significant cost/compute.

## E2E Regression Tests

24 browser tests via dev-browser (Playwright). Run after every deploy.

```bash
cp tests/e2e-regression.ts ~/code/work/dev-browser/skills/dev-browser/scripts/psr-regression.ts
cd ~/code/work/dev-browser/skills/dev-browser && npx tsx scripts/psr-regression.ts
```

Set `SCREENSHOTS=0` to skip screenshots. Exit code 1 on failure.
