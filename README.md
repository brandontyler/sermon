# PSR — Pastor Sermon Rating

Upload a sermon (audio, text, or YouTube link), get a data-driven score (0–100) with an 8-category breakdown. Built on Azure serverless + AI.

**Live site:** [howwas.church](https://howwas.church)

## Scoring Categories

| Category | Weight | Model |
|----------|--------|-------|
| Biblical Accuracy | 25% | o4-mini |
| Time in the Word | 20% | o4-mini |
| Passage Focus | 10% | o4-mini |
| Clarity | 10% | gpt-5-mini |
| Engagement | 10% | gpt-5-mini |
| Application | 10% | gpt-5-mini |
| Delivery | 10% | gpt-5-nano |
| Emotional Range | 5% | gpt-5-nano |

Scores are normalized by sermon type (expository/topical/survey) when classification confidence is high enough. Biblical Accuracy is denomination-neutral — it penalizes misquoting, not theological convictions.

## Quick Start

### Prerequisites

- Python 3.12+
- Node.js 18+
- [Azure Functions Core Tools](https://learn.microsoft.com/en-us/azure/azure-functions/functions-run-local) v4
- Azure subscription with resources deployed (see [docs/AZURE_SETUP.md](docs/AZURE_SETUP.md))

### Backend

```bash
cd api
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp local.settings.json.example local.settings.json  # fill in keys
func start
```

### Frontend

```bash
cd web
npm install
cp .env.production .env.local  # adjust API URL for local dev
npm run dev
```

### Tests

```bash
# Unit tests (130 tests, ~3s)
cd api && python -m pytest tests/ -v

# E2E browser tests (24 tests, requires dev-browser server)
cp tests/e2e-regression.ts ~/code/work/dev-browser/skills/dev-browser/scripts/psr-regression.ts
cd ~/code/work/dev-browser/skills/dev-browser && npx tsx scripts/psr-regression.ts
```

## Deploy

All deployment goes through a single script:

```bash
./infra/deploy.sh frontend   # Frontend only (Static Web Apps)
./infra/deploy.sh backend    # Backend only (Function App)
./infra/deploy.sh code       # Both frontend + backend
./infra/deploy.sh all        # Infra (Bicep) + code
./infra/deploy.sh status     # Check resource status
```

## Pipeline

```
Upload → Validate + Cosmos record → Blob Storage →
Wave 1 (parallel): Transcribe (AI Speech) + Parselmouth audio analysis →
Wave 2 (parallel): Pass 1 biblical (o4-mini), Pass 2 structure (gpt-5-mini),
                    Pass 3 delivery (gpt-5-nano), classify + segments + enrichment →
Fan-in → normalize → summary (gpt-5-nano) → store in Cosmos
```

Cost: ~$0.75/sermon. Processing time: ~3–5 minutes.

## Project Structure

```
api/                    Azure Functions backend
├── function_app.py     App init + blueprint registration
├── helpers.py          Shared utilities (_json_response, _require_admin, etc.)
├── routes/             HTTP endpoint blueprints
│   ├── sermons.py      Upload, list, get, edit, delete, translate, bonus
│   ├── feeds.py        RSS feed subscriptions + polling
│   ├── churches.py     Church CRUD
│   └── admin.py        Rescore endpoint
├── orchestrators.py    Durable Functions orchestrators + activity registrations
├── activities/         Pipeline activity functions
│   ├── scoring.py      LLM passes 1–4, classify, segments, summary
│   ├── transcription.py  Azure AI Speech + Parselmouth
│   ├── rescore.py      Selective rescore logic
│   ├── church.py       Auto-create church from pastor name
│   ├── misc.py         Update sermon, AI detection, content summary, RSS download
│   └── helpers.py      Shared clients (OpenAI, Cosmos, Blob)
├── schema.py           Data models, normalization, composite scoring
└── tests/              Unit tests

web/                    Next.js frontend (Static Web Apps)
├── src/app/            Pages (sermons, upload, churches, admin, dashboard)
├── src/components/     ScoreGauge, RadarView, TranscriptViewer, SermonDetail
└── src/lib/            API client, types

infra/                  Bicep templates + deploy script
docs/                   Architecture, research, rescore ops, Azure setup
tests/                  E2E browser regression tests
poc/                    Historical proof-of-concept scripts
.beads/                 Issue tracker (git-native, `br` CLI)
```

## Key Docs

| Doc | Purpose |
|-----|---------|
| [sermonplan.md](sermonplan.md) | Vision, pipeline detail, POC history, future phases |
| [docs/architecture.md](docs/architecture.md) | Platform architecture, data model, cost estimates |
| [docs/research.md](docs/research.md) | POC results, tools evaluation, model selection |
| [docs/rescore.md](docs/rescore.md) | Rescore operations (selective, staleness, workflows) |
| [docs/AZURE_SETUP.md](docs/AZURE_SETUP.md) | Azure resource provisioning guide |
| [AGENTS.md](AGENTS.md) | Context for coding agents working in this repo |

## API

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/sermons` | Upload audio, starts pipeline |
| `POST` | `/api/sermons/text` | Upload text, skips transcription |
| `POST` | `/api/sermons/youtube` | YouTube URL, fetches transcript |
| `GET` | `/api/sermons` | List all sermons |
| `GET` | `/api/sermons/{id}` | Sermon detail |
| `PATCH` | `/api/sermons/{id}` | Edit metadata (admin) |
| `DELETE` | `/api/sermons/{id}` | Delete sermon (admin) |
| `POST` | `/api/rescore` | Batch rescore (admin) |
| `GET/POST` | `/api/feeds` | RSS feed subscriptions (admin) |
| `GET/POST` | `/api/churches` | Church management |

Admin endpoints require `x-admin-key` header.
