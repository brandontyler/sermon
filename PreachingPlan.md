# PreachingPlan.md — PSR: Pastor Sermon Rating

## Vision

A public web platform where anyone can upload sermon video/audio and receive a data-driven **Pastor Sermon Rating (PSR)** — like a QBR for quarterbacks, but for preachers. The platform transcribes, analyzes, and scores sermons across multiple objective categories, then presents the results publicly with leaderboards, pastor profiles, and trend tracking.

Built entirely on Azure to showcase its AI, serverless, and data platform capabilities as a reference architecture.

---

## The PSR Score (0-100 Composite)

### Categories (Weighted)

| Category | Weight | What It Measures |
|----------|--------|-----------------|
| **Biblical Accuracy** | 25% | Scripture references detected, verified against passage context, cross-referenced with scholarly commentaries. Flags controversial interpretations rather than marking wrong. |
| **Time in the Word** | 20% | Percentage of sermon spent in scripture/biblical content vs personal anecdotes, historical illustrations, cultural references, and stories. Each segment classified. |
| **Passage Focus** | 10% | Time spent on the main/announced passage vs tangents and other topics. Measures how well the pastor stayed on their stated text. |
| **Clarity** | 10% | Logical structure, flow between points, clear transitions, easy to follow. Measured via topic coherence and structural analysis. |
| **Engagement** | 10% | Energy level, pacing variation, audience connection cues. Measured via speech rate changes, volume dynamics, pause usage. |
| **Application** | 10% | Practical takeaways, actionable points, real-world relevance. Detected via imperative language, "so what" moments. |
| **Delivery** | 10% | Speaking quality — filler words (um, uh, you know, like), confidence, articulation. Measured via speech analytics. |
| **Emotional Range** | 5% | Tone variation, passion, authenticity. Measured via sentiment arc and vocal prosody analysis. |

### Composite Score

- 0-100 scale calculated from weighted category scores
- No letter grades or tiers — just the number
- Each category also gets its own 0-100 score for drill-down

### Scholarly Verification Engine

Biblical Accuracy uses a three-layer approach:

1. **Curated Theological Database** — Bible text corpus (multiple translations: ESV, NIV, KJV, NASB), cross-reference tables, verse-to-topic mappings
2. **Commentary Corpus** — Established commentaries indexed for RAG retrieval, organized by theological tradition to avoid scoring bias:
   - **Reformed**: Calvin's Commentaries, Matthew Henry, Spurgeon, R.C. Sproul
   - **Wesleyan/Arminian**: Wesley's Notes, Adam Clarke, Ben Witherington III
   - **Baptist**: John Gill, A.T. Robertson, John MacArthur
   - **Broadly Evangelical**: D.A. Carson, N.T. Wright, Craig Keener, ESV Study Bible notes
   - **Historical/Academic**: F.F. Bruce, Bruce Metzger, Gordon Fee
   - The system identifies the pastor's likely theological tradition (via denomination tag or inference) and weights verification accordingly — a Reformed pastor teaching election from Ephesians 1 shouldn't be flagged just because Arminian commentators disagree
3. **AI Cross-Reference** — Azure OpenAI compares the pastor's claims about a passage against the commentary corpus and flags:
   - ✅ **Aligned** — Supported by commentators within the pastor's tradition AND not contradicted by the passage text
   - ⚠️ **Debated** — Valid interpretation within one tradition but contested by others (shows sources for both sides). Does NOT penalize the score — only informs the viewer
   - ❌ **Contradicts** — Claims something the passage text plainly does not say, or misattributes a quote/reference. Reserved for clear factual errors, not theological disagreements

**Important design principle:** Biblical Accuracy measures whether the pastor *correctly handles the text they reference* — not whether their theology is "right." A Calvinist and an Arminian preaching Romans 9 can both score 90+ if they accurately represent what the text says and honestly engage the interpretive questions. The score penalizes misquoting, out-of-context proof-texting, and factual errors — not denominational convictions.

---

## Transcription & Analytics Pipeline

### Data Points Extracted

**Speech Analytics:**
- Full transcript with timestamps and speaker diarization
- Words per minute (overall + per segment)
- Filler word count and locations (um, uh, you know, like, so, right)
- Pause duration and frequency
- Volume/loudness over time
- Speech rate variation (monotone vs dynamic)

**Content Analytics:**
- Scripture references detected (book, chapter, verse) with confidence scores
- Segment classification: Scripture Reading | Biblical Teaching | Personal Anecdote | Historical Illustration | Cultural Reference | Humor | Application | Prayer | Transition
- Main passage identification and time-on-passage tracking
- Topic extraction and coherence scoring
- Sentiment arc (emotional journey from intro to conclusion)
- Key themes and theological concepts

**Structural Analytics:**
- Introduction length and hook quality
- Number of main points
- Conclusion/call-to-action detection
- Total sermon duration
- Time distribution across segments (pie chart data)

---

## Azure Architecture

### Reference Architecture — Azure Services Showcased

```
┌─────────────────────────────────────────────────────────────────┐
│                        FRONTEND                                  │
│  Azure Static Web Apps (Next.js + TypeScript)                   │
│  Azure CDN / Front Door                                          │
│  Azure AD B2C (auth — email + Google/Microsoft/Apple)           │
└──────────────────────────┬──────────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────────┐
│                        API LAYER                                 │
│  Azure API Management                                            │
│  Azure Functions (Python — serverless)                           │
└──────────┬───────────────┬──────────────┬───────────────────────┘
           │               │              │
┌──────────▼───┐  ┌───────▼────────┐  ┌──▼──────────────────────┐
│   UPLOAD     │  │  PROCESSING    │  │  DATA & SEARCH          │
│              │  │                │  │                          │
│ Azure Blob   │  │ Azure AI       │  │ Azure Cosmos DB          │
│ Storage      │  │ Speech Service │  │ (sermon metadata,        │
│ (video/audio)│  │ (transcription │  │  ratings, profiles)      │
│              │  │  + diarization)│  │                          │
│ Azure Media  │  │                │  │ Azure AI Search          │
│ Services     │  │ Azure OpenAI   │  │ (full-text + semantic    │
│ (transcode)  │  │ (GPT-4 for    │  │  search across sermons)  │
│              │  │  analysis,     │  │                          │
│              │  │  scoring,      │  │ Azure Cache for Redis    │
│              │  │  commentary    │  │ (leaderboards, hot data) │
│              │  │  verification) │  │                          │
└──────────────┘  │                │  └──────────────────────────┘
                  │ Azure AI       │
                  │ Language       │
                  │ (sentiment,    │
                  │  key phrases,  │
                  │  topic model)  │
                  └────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                     ORCHESTRATION                                │
│  Azure Service Bus (queue sermon processing jobs)               │
│  Azure Durable Functions (multi-step pipeline orchestration)    │
│  Azure Event Grid (event-driven triggers)                       │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                     MONITORING & OPS                              │
│  Azure Monitor + Application Insights                           │
│  Azure Key Vault (API keys, secrets)                            │
│  Azure DevOps (CI/CD pipelines)                                 │
└─────────────────────────────────────────────────────────────────┘
```

### Service Breakdown

| Azure Service | Purpose |
|--------------|---------|
| **Static Web Apps** | Host Next.js frontend with built-in auth integration |
| **Azure AD B2C** | User auth — email signup + Google/Microsoft/Apple social login |
| **API Management** | API gateway, rate limiting, analytics |
| **Azure Functions** | Serverless API endpoints and processing logic |
| **Durable Functions** | Orchestrate the multi-step sermon analysis pipeline |
| **Blob Storage** | Store uploaded video/audio files |
| **Media Services** | Transcode video, extract audio track for speech processing |
| **AI Speech Service** | Transcription with speaker diarization, word-level timestamps |
| **Azure OpenAI (GPT-4)** | Sermon analysis, scoring, segment classification, commentary cross-reference |
| **AI Language Service** | Sentiment analysis, key phrase extraction, topic modeling |
| **Cosmos DB** | NoSQL store for sermon metadata, ratings, pastor profiles, user data |
| **AI Search** | Full-text + semantic search across all sermons and transcripts |
| **Redis Cache** | Leaderboard caching, hot pastor profiles, trending sermons |
| **Service Bus** | Queue processing jobs, decouple upload from analysis |
| **Event Grid** | Event-driven triggers between pipeline stages |
| **Key Vault** | Secure storage for API keys and secrets |
| **Monitor + App Insights** | Observability, performance tracking, error alerting |
| **Azure DevOps** | CI/CD, infrastructure as code (Bicep), automated testing |
| **Front Door / CDN** | Global content delivery, DDoS protection |

---

## Processing Pipeline

### Upload Flow

```
User uploads video/audio file directly
    │
    ▼
1. Azure Function: Validate upload (file type, size, duration check), create sermon record in Cosmos DB (status: processing)
    │
    ▼
2. Store file in Azure Blob Storage
    │
    ▼
3. Service Bus: Queue processing job
    │
    ▼
4. Durable Function Orchestrator kicks off:
    │
    ├─► Step 1: Media Services — extract audio track (if video)
    │
    ├─► Step 2: AI Speech Service — transcribe with diarization + word timestamps
    │       Max duration: 2 hours supported
    │
    ├─► Step 3: AI Language Service — sentiment analysis, key phrases, topics
    │
    ├─► Step 4: Azure OpenAI — segment classification
    │       Classify each segment: Scripture | Teaching | Anecdote | Illustration |
    │       Cultural Reference | Humor | Application | Prayer | Transition
    │
    ├─► Step 5: Azure OpenAI — scripture detection & verification
    │       Detect all scripture references
    │       Cross-reference against Bible text corpus
    │       Verify interpretation against commentary corpus (RAG)
    │       Flag: aligned / controversial / contradicts
    │
    ├─► Step 6: Azure OpenAI — PSR scoring
    │       Score each category 0-100 based on extracted data
    │       Calculate weighted composite PSR score
    │       Generate natural language summary of strengths/weaknesses
    │
    ├─► Step 7: Store results in Cosmos DB, update search index
    │
    └─► Step 8: Event Grid → notify user (email) that analysis is complete
```

---

## Data Model (Cosmos DB)

### Sermon Document
```json
{
  "id": "sermon-uuid",
  "pastorId": "pastor-uuid",
  "uploadedBy": "user-uuid",
  "title": "The Power of Grace",
  "date": "2026-02-22",
  "denomination": "non-denominational",
  "church": "Grace Community Church",
  "duration": 2847,
  "mediaUrl": "https://blob.../sermon.mp4",
  "status": "complete",
  "moderation": {
    "status": "approved",
    "flags": [],
    "reviewedAt": "2026-02-22T10:05:00Z"
  },
  "transcript": {
    "fullText": "...",
    "segments": [
      {
        "start": 0.0,
        "end": 45.2,
        "speaker": "pastor",
        "text": "...",
        "type": "introduction",
        "sentiment": 0.72
      }
    ],
    "wordCount": 4521,
    "wordsPerMinute": 142
  },
  "analytics": {
    "fillerWords": { "um": 23, "uh": 12, "you know": 8, "like": 15 },
    "fillerWordsTotal": 58,
    "scriptureReferences": [
      {
        "reference": "Romans 8:28",
        "timestamp": 312.5,
        "context": "pastor's statement about the verse",
        "verification": "aligned",
        "commentarySources": ["Matthew Henry", "Spurgeon"]
      }
    ],
    "segmentBreakdown": {
      "scriptureReading": 0.12,
      "biblicalTeaching": 0.35,
      "personalAnecdote": 0.18,
      "historicalIllustration": 0.08,
      "culturalReference": 0.05,
      "humor": 0.03,
      "application": 0.12,
      "prayer": 0.04,
      "transition": 0.03
    },
    "mainPassage": "Romans 8:28-30",
    "timeOnMainPassage": 0.47,
    "sentimentArc": [0.5, 0.6, 0.7, 0.8, 0.65, 0.9, 0.85],
    "themes": ["grace", "sovereignty", "suffering", "hope"]
  },
  "psr": {
    "composite": 78,
    "categories": {
      "biblicalAccuracy": 85,
      "timeInTheWord": 72,
      "passageFocus": 68,
      "clarity": 82,
      "engagement": 76,
      "application": 80,
      "delivery": 74,
      "emotionalRange": 71
    },
    "summary": "Strong biblical foundation with good application. Could improve passage focus — 18% of time spent on tangential topics. Delivery solid but 58 filler words is above average. Scripture verification: 8 references, all aligned with mainstream scholarship.",
    "strengths": ["Biblical grounding", "Practical application", "Clear structure"],
    "improvements": ["Reduce filler words", "More time on main passage", "Vary emotional tone"]
  },
  "createdAt": "2026-02-22T10:00:00Z"
}
```

### Pastor Profile Document
```json
{
  "id": "pastor-uuid",
  "name": "Pastor John Smith",
  "claimed": true,
  "claimedBy": "user-uuid",
  "optedOut": false,
  "visibility": "public",
  "denomination": "Baptist",
  "church": "First Baptist Church",
  "location": "Dallas, TX",
  "sermonCount": 47,
  "averagePsr": 76,
  "psrTrend": [72, 74, 75, 76, 78, 76],
  "categoryAverages": {
    "biblicalAccuracy": 82,
    "timeInTheWord": 70,
    "passageFocus": 65,
    "clarity": 80,
    "engagement": 74,
    "application": 78,
    "delivery": 71,
    "emotionalRange": 68
  },
  "followers": 234,
  "topStrengths": ["Biblical Accuracy", "Application"],
  "topImprovements": ["Passage Focus", "Delivery"]
}
```

---

## Frontend Features

### Pages

| Page | Description |
|------|-------------|
| **Home** | Trending sermons, top-rated pastors, recent uploads, search bar |
| **Upload** | Drag-and-drop video/audio file. Tag pastor name, church, denomination, date. Accepted formats: MP3, MP4, WAV, M4A, WEBM. Max 2 hours / 2GB. |
| **Sermon Detail** | Full PSR scorecard, transcript with segment highlighting, scripture verification results, analytics charts (time breakdown pie, sentiment arc line, filler word timeline) |
| **Pastor Profile** | Photo, bio, church, denomination. PSR trend over time, category radar chart, sermon history, strengths/improvements. Follow button. Claim profile option. |
| **Leaderboards** | Top PSR this month, most improved, most sermons analyzed. Filter by denomination, time period |
| **Search** | Full-text + semantic search across all sermons and transcripts |
| **My Account** | Uploaded sermons, followed pastors, playlists |

### Key UI Components

- **PSR Gauge** — circular gauge showing 0-100 composite score with color gradient (red → yellow → green)
- **Category Radar Chart** — 8-axis radar showing all category scores at a glance
- **Segment Timeline** — horizontal bar showing sermon broken into colored segments (scripture=blue, anecdote=orange, application=green, etc.)
- **Sentiment Arc** — line chart showing emotional journey from intro to conclusion
- **Scripture Verification Cards** — each reference with ✅/⚠️/❌ and commentary sources
- **Filler Word Heatmap** — timeline showing where filler words cluster
- **Trend Line** — pastor's PSR over time with moving average

---

## MVP Scope — Phase 0: "Does This Thing Work?"

The goal: **upload a sermon, get a score, see the results.** Nothing else.

### In Scope
- Upload audio file (MP3, WAV, M4A — audio only, skip video transcoding for now)
- Basic auth (Azure AD B2C — email signup only, no social login yet)
- Transcription via Azure AI Speech (with timestamps)
- Segment classification via Azure OpenAI (scripture, teaching, anecdote, application, etc.)
- Scripture detection (identify references, verify against Bible text)
- PSR scoring — all 8 categories + composite score
- **One page that matters:** sermon detail page with scorecard, transcript, segment timeline
- Upload page (simple drag-and-drop, tag pastor name + church)
- Home page (list of recently analyzed sermons — no ranking, just a feed)
- English only
- Max 1 hour sermon length (keeps processing costs low while proving the concept)

### Explicitly NOT in MVP
- Video upload / transcoding (audio only — way simpler pipeline)
- Social login (Google/Microsoft/Apple) — email-only auth is fine for now
- Pastor profiles / claiming / opt-out
- Leaderboards
- Search
- Follow pastors / playlists
- Content moderation (manual review queue, admin dashboard)
- Reporting
- Commentary corpus RAG for Biblical Accuracy (use Azure OpenAI's built-in knowledge for v0, build the RAG layer in Phase 1)
- 2-hour sermon support (cap at 1 hour to keep costs predictable)

### Why This Cut
1. **Proves the core value** — can AI meaningfully rate a sermon? That's the whole bet
2. **Exercises the hard parts** — transcription pipeline, GPT scoring, Durable Functions orchestration
3. **Demo-able** — upload a sermon, wait a few minutes, see a beautiful scorecard
4. **Buildable in focused sessions** — two devs, a few weekends, no scope creep
5. **Cheap** — audio-only + 1hr cap keeps Azure costs under $50/mo during dev

### MVP Azure Services (Minimal Set)

| Service | Purpose |
|---------|---------|
| **Static Web Apps** | Next.js frontend (free tier) |
| **Azure AD B2C** | Email auth (free up to 50K MAU) |
| **Azure Functions** | API + processing logic (consumption plan) |
| **Durable Functions** | Pipeline orchestration |
| **Blob Storage** | Store uploaded audio files |
| **AI Speech Service** | Transcription with timestamps |
| **Azure OpenAI (GPT-4)** | Analysis, scoring, segment classification |
| **Cosmos DB** | Sermon metadata + results (serverless tier) |
| **Key Vault** | Secrets |

**Not needed for MVP:** API Management, Service Bus, Event Grid, Redis Cache, AI Search, Media Services, Front Door, AI Language Service, Monitor/App Insights. Add them when scale demands it.

### MVP Estimated Cost
~$20-50/mo during development (Cosmos serverless, Functions consumption, pay-per-sermon for Speech + OpenAI). No fixed-cost services.

---

## Content Moderation

*Deferred to Phase 1. For MVP, uploads are invite-only / low volume — manual oversight is sufficient.*

---

## Pastor Consent & Opt-Out

### How It Works

- **Anyone can upload** a sermon and tag a pastor — this is core to the platform (sermons are public content)
- **Pastors can claim their profile** — verify identity via email from their church domain, link to church website, or manual review
- **Claimed pastors can:**
  - Edit their bio, photo, and church info
  - See analytics dashboards for their own sermons
  - Request removal of specific sermons (reviewed within 48 hours)
  - Set their profile to **unlisted** (sermons still analyzed but hidden from leaderboards and search)
  - Fully **opt out** — all sermons and profile data removed, pastor name added to a block list to prevent re-upload
- **Unclaimed profiles** are public by default but display a "Not yet claimed" badge
- **DMCA/takedown process** — standard takedown request form for copyright claims

### Data Retention

- When a pastor opts out, sermon data is soft-deleted (retained 30 days for appeals, then hard-deleted)
- Media files are deleted immediately on opt-out
- Aggregated/anonymized analytics may be retained for platform-level statistics

---

## Infrastructure as Code

- **Bicep** templates for all Azure resources
- **Azure DevOps** pipelines for CI/CD
- Environments: dev → staging → production
- All secrets in **Azure Key Vault**
- Cosmos DB with autoscale throughput
- Blob Storage with lifecycle policies (move old media to cool/archive tier)

---

## Tech Stack Summary

| Layer | Technology |
|-------|-----------|
| Frontend | Next.js, TypeScript, Tailwind CSS |
| Auth | Azure AD B2C |
| API | Azure Functions (Python) |
| Orchestration | Azure Durable Functions (Python) |
| Database | Azure Cosmos DB (NoSQL) |
| Search | Azure AI Search |
| Cache | Azure Cache for Redis |
| Storage | Azure Blob Storage |
| AI - Speech | Azure AI Speech Service |
| AI - Language | Azure AI Language Service |
| AI - LLM | Azure OpenAI (GPT-4) |
| AI - Video | Azure AI Video Indexer (future phase) |
| Messaging | Azure Service Bus + Event Grid |
| CDN | Azure Front Door |
| IaC | Bicep |
| CI/CD | Azure DevOps |
| Monitoring | Azure Monitor + Application Insights |

---

## Estimated Azure Costs (MVP, Low Traffic)

| Service | Estimated Monthly |
|---------|------------------|
| Static Web Apps | Free tier |
| Azure Functions | ~$5 (consumption) |
| Cosmos DB | ~$25 (autoscale, low RU) |
| Blob Storage | ~$5-20 (depending on uploads) |
| AI Speech | ~$1/hr of audio transcribed |
| Azure OpenAI | ~$0.50-2.00 per sermon (multiple analysis passes on 8-10K word transcripts) |
| AI Search | ~$250 (S1 tier for semantic/vector search) |
| Redis Cache | ~$15 (basic) |
| Service Bus | ~$10 (basic) |
| AD B2C | Free up to 50K MAU |
| **Total estimate** | **~$350-500/mo at low volume** |

*Costs scale with usage — primarily driven by sermon processing (Speech + OpenAI tokens). At 100 sermons/month, OpenAI alone could be $50-200. AI Search is a fixed cost regardless of volume — consider starting with basic full-text search and adding semantic search when traffic justifies it.*

---

## Proof of Concept (Completed)

A minimal end-to-end POC lives in `poc/psr_poc.py`. It validates the core pipeline: audio in → transcript → AI analysis → PSR score out.

### What the POC Does

1. **Transcribe** — Takes an MP3 file, sends it to OpenAI Whisper API, gets back timestamped text
2. **Analyze** — Sends the transcript to GPT-4o with a structured prompt requesting: delivery score, filler word counts, scripture references, segment breakdown, strengths, and improvements
3. **Score** — Produces a PSR Delivery score (0-100) with full breakdown
4. **Output** — Writes `poc/psr_result.json` with the complete analysis and prints a scorecard to the terminal

### How to Run It

```bash
# Mock mode — no API key needed, uses a built-in sample sermon transcript
python3 poc/psr_poc.py --mock

# Real mode — transcribes and analyzes an actual MP3 file
export OPENAI_API_KEY="sk-..."
python3 poc/psr_poc.py path/to/sermon.mp3
```

### What the POC Proved

- The full pipeline works: audio → text → structured AI analysis → scored output
- GPT-4o can reliably return structured JSON with filler word counts, scripture detection, segment classification, and a 0-100 score
- Whisper handles sermon-length audio and produces clean transcripts
- The mock run scored a sample Romans 8:28 sermon at **74/100** on Delivery, caught 13 filler words, identified 2 scripture references, and generated actionable strengths/improvements

### What's Different from the Full Platform

| POC | Full Platform |
|-----|--------------|
| OpenAI Whisper | Azure AI Speech Service (with diarization) |
| OpenAI GPT-4o | Azure OpenAI GPT-4 |
| Scores 1 category (Delivery) | Scores all 8 PSR categories |
| CLI script | Web app with upload UI |
| JSON file output | Cosmos DB + frontend scorecard |
| No auth | Azure AD B2C |
| No scripture verification | Commentary corpus RAG |

### Beginner's Guide: How This Pipeline Works (Step by Step)

If you're new to building AI-powered apps, here's what's happening under the hood and how to learn from it:

**Step 1: Understand the input/output contract**
- Input: an audio file (MP3, WAV, etc.)
- Output: a structured JSON object with scores, counts, and text analysis
- Everything in between is just transforming data from one shape to another

**Step 2: Audio → Text (Transcription)**
- The Whisper API (or Azure AI Speech) takes raw audio and returns text with timestamps
- This is a "black box" API call — you send a file, you get text back
- Key concept: **API as a service** — you don't train the model, you just call it
- Try it: change the audio file and see how the transcript changes
- Learn more: [OpenAI Whisper docs](https://platform.openai.com/docs/guides/speech-to-text), [Azure AI Speech docs](https://learn.microsoft.com/en-us/azure/ai-services/speech-service/)

**Step 3: Text → Structured Analysis (LLM prompting)**
- The transcript text is sent to GPT-4o with a **system prompt** that tells it exactly what JSON structure to return
- This is **prompt engineering** — the art of telling the AI what you want in a way it understands
- Key concept: `response_format={"type": "json_object"}` forces the model to return valid JSON (no markdown, no prose)
- Try it: edit the system prompt in `analyze()` to add a new field (e.g., `"humor_count"`) and see it appear in the output
- Learn more: [OpenAI structured outputs](https://platform.openai.com/docs/guides/structured-outputs)

**Step 4: Display the results**
- The script just prints to terminal and writes a JSON file
- In the full platform, this becomes a web UI with charts and gauges
- Key concept: **separation of concerns** — the analysis engine doesn't care how results are displayed

**How to experiment:**
1. Run `--mock` first to see the flow without any API costs
2. Get an OpenAI API key from [platform.openai.com](https://platform.openai.com)
3. Find a sermon MP3 (most churches post them online) and run it through
4. Edit the system prompt in `analyze()` to score different things
5. Compare results across different sermons — does the scoring feel right?

**Key programming concepts used:**
- **API calls** — sending HTTP requests to external services (Whisper, GPT-4o)
- **JSON parsing** — converting text responses into structured data
- **Prompt engineering** — crafting instructions for an LLM to get reliable, structured output
- **CLI argument parsing** — `argparse` for handling command-line flags
- **File I/O** — reading audio files, writing JSON results

---

## Next Steps

### Phase 0 — MVP: "Does This Thing Work?" (Current Target)
1. Set up Azure resource group + Bicep templates for minimal services (Functions, Blob, Cosmos serverless, Speech, OpenAI, Key Vault)
2. Build upload → transcribe → store pipeline (audio only, Durable Functions orchestration)
3. Build PSR scoring engine with Azure OpenAI (all 8 categories, using GPT-4's built-in Bible knowledge)
4. Build frontend: upload page + sermon detail page with scorecard, transcript, segment timeline
5. Basic auth with Azure AD B2C (email only)
6. Deploy to dev environment, test with real sermons

### Phase 1 — Public Launch
7. Add video upload support (Media Services for audio extraction)
8. Build commentary corpus RAG for denomination-aware Biblical Accuracy scoring
9. Add pastor profiles, claiming workflow, and opt-out mechanism
10. Add leaderboards and search (basic full-text first)
11. Content moderation pipeline (automated checks + admin review queue)
12. Social login (Google/Microsoft/Apple)
13. Extend to 2-hour sermon support
14. Polish, test, deploy to production

### Phase 2 — Growth
15. Semantic/vector search upgrade (AI Search)
16. Follow pastors, playlists, user account features
17. Video-specific analysis (Video Indexer)
18. Multi-language support
19. Church organization accounts
20. Sermon comparison (side-by-side)
21. API for third-party integrations

---

## Team & Collaboration

### Who's Building This

| Person | Background | Role |
|--------|-----------|------|
| **Brandon** | AWS developer, software engineer, experienced with AI coding agents (kiro-cli, Claude Code) | Architecture, AI agent workflow, mentoring on dev process |
| **Friend** | Azure sales data engineer, developer-savvy | Azure expertise, data pipeline design, learning to build from idea to product |

### The Goal

This is a **collaborative learning project** with two purposes:
1. **Build PSR** — take the idea from plan to working product on Azure
2. **Show the process** — Brandon demonstrates how to use AI coding agents to go from idea to code, while learning Azure alongside his friend who knows the platform

### Development Tooling — Different Tools, Same Repo

Each developer uses the AI tools they have access to. The code is the common ground.

**Brandon's Stack:**
- **kiro-cli** — primary AI coding agent (terminal-first, autonomous, reads codebase and drives edits). This is what's running right now in this Discord channel
- **`az` CLI + `azd`** — learning Azure alongside the project
- Workflow: terminal-driven, agent does the heavy lifting

**Friend's Stack (Microsoft Employee — Full Access):**
- **GitHub Copilot** (VS Code) — inline completions, chat, code generation. Backed by GPT-4o. Free with Microsoft employment
- **GitHub Copilot CLI** (`gh copilot`) — terminal command suggestions and explanations
- **GitHub Copilot Coding Agent** — can be assigned GitHub issues and works autonomously in PRs (runs in cloud, not local). Closest Microsoft equivalent to Claude Code
- **`az` CLI + `azd` + `func`** — already knows these
- Workflow: VS Code-driven, Copilot assists inline

**The Gap (and How We Bridge It):**
Microsoft doesn't have a true kiro-cli equivalent — a local, terminal-first, autonomous coding agent that reads your whole codebase, makes multi-file edits, runs commands, and iterates in a loop. Copilot is excellent at *assisting* but not at *driving*.

How we work around this:
1. Both devs work on the same GitHub repo — tool choice is personal, code is shared
2. Brandon screen-shares / works in Discord so friend can see the CLI agent workflow in action
3. Friend uses Copilot Coding Agent for autonomous PR work (assign it a GitHub issue, it opens a PR)
4. For pair sessions: Brandon drives with kiro-cli while friend watches and learns the agent-first approach
5. GPT-4o (which powers Copilot) is a strong model — the gap is in the *agent harness*, not the model quality

**Core Azure CLI Tools (Both Developers):**
- **`az` (Azure CLI)** — Azure resource management. Install: `curl -sL https://aka.ms/InstallAzureCLIDeb | sudo bash`
- **`azd` (Azure Developer CLI)** — scaffold, provision, deploy. Install: `curl -fsSL https://aka.ms/install-azd.sh | bash`
- **`func` (Azure Functions Core Tools)** — local Functions dev/test. Install: `npm i -g azure-functions-core-tools@4`
- **`bicep`** — Azure IaC (bundled with `az`)

**Setup Checklist:**

Brandon:
- [ ] Install `az` CLI and run `az login`
- [ ] Install `azd` CLI
- [ ] Install `func` (Azure Functions Core Tools)
- [ ] kiro-cli (already set up and running)

Friend:
- [ ] `az` CLI + `azd` + `func` (likely already has these)
- [ ] VS Code + GitHub Copilot (has via Microsoft)
- [ ] `gh` CLI + Copilot CLI extension: `gh extension install github/gh-copilot`
- [ ] Enable Copilot Coding Agent on the shared repo (Settings → Copilot → Coding agent)

Shared:
- [ ] Create shared Azure resource group
- [ ] Set up GitHub repo with branch protection
- [ ] Add both devs as collaborators
