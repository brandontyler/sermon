# Agent Instructions

## Project Overview

PSR (Pastor Sermon Rating) — A public web platform where anyone can upload sermon audio and receive a data-driven score (0-100 composite), like a QBR for quarterbacks but for preachers. Built on Azure serverless + AI services.

```
Upload Audio → Transcribe (AI Speech) → Analyze (GPT-4 + Parselmouth) → PSR Score → Display
```

**Current Phase:** MVP (Phase 0) — "Does This Thing Work?"

## Key Docs

| Doc | Purpose |
|-----|---------|
| `sermonplan.md` | Vision, PSR scoring categories, MVP scope, pipeline, phases |
| `docs/architecture.md` | Full platform architecture, data model, cost estimates |
| `docs/research.md` | Competitive landscape, POC results (#1-4), tools evaluation |
| `docs/team.md` | Who's building this, dev tooling, setup |

## Issue Tracking (Beads)

Uses **br** (beads-rust) — git-native, AI-friendly task tracker stored in `.beads/`.

| Command | Purpose |
|---------|---------|
| `br ready` | Find work with no blockers (START HERE) |
| `br list` | List all issues |
| `br show <id>` | View details + blockers |
| `br update <id> --claim` | Claim work (atomic: assignee + in_progress) |
| `br close <id> --reason "..."` | Complete work |
| `br create "Title" -p 1 -t task` | Create task (P0-P3) |
| `br dep add <child> <parent>` | Add blocker |
| `br sync --flush-only` | Export DB → JSONL (then `git add .beads/ && git commit`) |
| `br sync --import-only` | Import JSONL → DB (after git pull) |

Issue IDs: `bd-xxx` (lowercase). Types: epic, feature, task, bug.

After clone/checkout: `br sync --import-only`. After git pull: `br sync --import-only`.

### Beads Workflow

- Check `br ready` before starting work
- Claim issues with `br update <id> --claim` before working on them
- Close issues with `br close <id> --reason "..."` when done
- Create new issues for discovered work rather than leaving TODOs in code
- Flush after mutations: `br sync --flush-only`

## Tech Stack (MVP)

| Layer | Tech |
|-------|------|
| Frontend | Next.js on Azure Static Web Apps |
| API + Processing | Azure Functions (consumption plan) |
| Orchestration | Durable Functions |
| Storage | Azure Blob Storage (audio), Cosmos DB serverless (metadata + results) |
| Transcription | Azure AI Speech (timestamps + diarization) |
| Analysis | Azure OpenAI GPT-4 (scoring, classification, verification) |
| Audio Metrics | Parselmouth (pitch, volume, pauses) |
| Secrets | Azure Key Vault |

## POC Code

POC scripts live in `poc/`. Sample sermons in `poc/samples/` (Piper sermons, MP3).

| File | What it does |
|------|-------------|
| `poc/psr_poc.py` | End-to-end PSR scoring proof of concept |
| `poc/scripture_analyzer.py` | Scripture detection + verification |
| `poc/audio_analysis_poc.py` | Parselmouth audio metrics extraction |
| `poc/sermon_comparison.py` | Cross-sermon comparison (POC #4) |
