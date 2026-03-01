# Architecture — Full Platform Vision

The full-scale PSR architecture for when we grow beyond MVP. See [sermonplan.md](../sermonplan.md) for the MVP scope and current focus.

---

## Reference Architecture — Azure Services Showcased

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

## Service Breakdown

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

## Full Tech Stack

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

## Full Processing Pipeline

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

## Full Frontend Features (Post-MVP)

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

## Estimated Azure Costs (Full Platform, Low Traffic)

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

## Post-MVP: AWS vs Azure Head-to-Head Comparison

Once both cloud stacks are deployed and processing sermons, run a structured comparison:

**Deployment Complexity**
- Lines of IaC (Bicep vs CDK/CloudFormation)
- Number of services to configure
- Time from zero to deployed (first deploy)
- CI/CD pipeline complexity

**Performance**
- Cold start latency (Functions vs Lambda)
- End-to-end sermon processing time (upload → score ready)
- API response times under load

**Cost**
- Monthly run cost at idle / low usage (MVP scale)
- Cost per sermon processed
- Free tier coverage — what's actually free vs what bleeds over

**Developer Experience**
- Local dev/debug story
- Logging & observability setup effort
- How easy is it to iterate and redeploy

*Tracked as bead `bd-1ym`.*
