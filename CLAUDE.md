# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

PSR (Pastor Sermon Rating) — upload sermon audio, get a 0-100 composite score. Azure serverless + AI. Currently in MVP phase (Phase 0).

See `AGENTS.md` for scoring categories/weights, pipeline summary, issue tracking workflow (`br` CLI), and cost controls. Read it before starting any significant work.

## Commands

### Frontend (`web/`)
```bash
npm install
npm run dev          # Dev server on port 3000
npm run build        # Static export to out/
npm run lint
npm test             # Jest unit tests
npm run test:coverage
```

### Backend (`api/`)
```bash
python -m venv .venv && source .venv/Scripts/activate   # Windows
pip install -r requirements.txt
cp local.settings.json.example local.settings.json       # Fill in Azure keys
func start           # Local Functions emulator (requires Azure Functions Core Tools)
python -m pytest tests/ -v                               # 130 unit tests, ~3s
python -m pytest tests/test_activities.py::TestClass::test_name -v  # Single test
```

### Deploy (`infra/`)
```bash
./infra/deploy.sh frontend   # Frontend only
./infra/deploy.sh backend    # Backend only
./infra/deploy.sh code       # Frontend + backend
./infra/deploy.sh all        # Infra (Bicep) + code
./infra/deploy.sh status     # Check Azure resource state
```

### Issue Tracking
```bash
br ready             # Find work with no blockers (start here)
br list
br show <id>
br update <id> --claim
br close <id> --reason "..."
br sync --flush-only # Export to JSONL, then git add + commit
```

## Architecture

Two deployable units:

**`api/` — Azure Functions (Python 3.12)**
- `function_app.py` — app init and route registration
- `routes/` — HTTP endpoints: `sermons.py`, `feeds.py`, `churches.py`, `admin.py`, `users.py`
- `orchestrators.py` — Durable Functions orchestrators with retry policies; manages the two-wave pipeline
- `activities/` — individual pipeline steps (transcription, audio analysis, 4 scoring passes, enrichment, summary)
- `schema.py` — Cosmos DB document models, score normalization, `PIPELINE_VERSION`, `PASS_HASHES` for staleness detection
- `helpers.py` — shared CORS, admin auth (`x-admin-key` header), validation utilities
- `host.json` — 10-minute function timeout, Durable task hub `PsrTaskHub`

**`web/` — Next.js 15 (TypeScript, static export)**
- `src/app/` — pages: home, sermon list, sermon detail, upload, admin, dashboard
- `src/components/` — ScoreGauge, RadarView, TranscriptViewer, Nav
- `src/lib/` — API client, shared types, themes, tenant config
- Deployed as Azure Static Web Apps; `/api/*` routes proxied to the linked Function App
- `next.config.ts` sets `output: "export"` — no Next.js server, purely static

**`infra/`** — Bicep IaC + `deploy.sh`

**`docs/`** — architecture.md, research.md, rescore.md, AZURE_SETUP.md, frontend-spec.md, security-review.md

## Pipeline Details

```
Upload → Validate + Cosmos record → Blob Storage →
  Wave 1 (parallel): Azure AI Speech transcription + Parselmouth audio analysis →
  Wave 2 (throttle-aware parallel):
    Pass 1: Biblical Analysis (o4-mini)  — biblicalAccuracy, timeInTheWord, passageFocus
    Pass 2: Structure & Content (gpt-5-mini) — clarity, application, engagement
    Pass 3: Delivery (gpt-5-nano) — delivery, emotionalRange
    Classify: sermon type + metadata (gpt-5-nano)
    Segments: transcript segment labels (gpt-5-nano)
    Pass 4: Enrichment (gpt-5-nano) — biblical languages, church history
  Fan-in → score normalization (pure code in schema.py) → summary (gpt-5-nano) → Cosmos
```

Cost: ~$0.75/sermon. Full rescore: ~$1.50, ~90 minutes. **Never trigger `POST /api/rescore {"all": true}` without explicit approval from Brandon or Orlando.** Single-sermon and selective rescores are fine.

## Non-Obvious Patterns

- **Score normalization is type-aware**: expository/topical/survey sermons get different normalization curves. Classification confidence gates the bump: <80% → no normalization, 80–90% → half bump, >90% → full bump.
- **Staleness detection**: `schema.py:PASS_HASHES` stores a hash of each pass's prompt + model. If the hash changes, the pass is considered stale and eligible for rescore. `PIPELINE_VERSION` tracks the overall version.
- **Cosmos DB**: single `sermons` container, partition key `/id`. All feed queries are cross-partition — acceptable for MVP scale.
- **Admin auth**: MVP uses `x-admin-key` header or SWA client principal. No full auth yet (Azure AD B2C is planned for Phase 1).
- **Frontend cold-start handling**: retry logic with 2s/4s/6s exponential backoff on API calls to handle Azure Functions cold starts.
- **Static export constraints**: avoid server-side Next.js features. Dynamic routes use `useEffect` + `window.location` to avoid hydration races.
- **Local development**: uses Azurite (Azure Storage emulator) for Blob/Queue/Table. Connection strings for Azurite are in `local.settings.json.example`.

## E2E Tests

24 Playwright browser tests in a separate `dev-browser` project:
```bash
cp tests/e2e-regression.ts ~/code/work/dev-browser/skills/dev-browser/scripts/psr-regression.ts
cd ~/code/work/dev-browser/skills/dev-browser && npx tsx scripts/psr-regression.ts
# SCREENSHOTS=0 to skip screenshots; exits 1 on failure
```
Run after every deploy.
