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

Biblical Accuracy uses a two-layer approach:

1. **Curated Theological Database** — Bible text corpus (multiple translations: ESV, NIV, KJV, NASB), cross-reference tables, verse-to-topic mappings
2. **Commentary Corpus** — Established commentaries (Matthew Henry, Spurgeon, Calvin, Wesley, modern evangelical/reformed scholars) indexed for RAG retrieval
3. **AI Cross-Reference** — Azure OpenAI compares the pastor's claims about a passage against the commentary corpus and flags:
   - ✅ Aligned with mainstream scholarship
   - ⚠️ Controversial/debated interpretation (with sources for both sides)
   - ❌ Contradicts the passage text or broad scholarly consensus

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
│  Azure Static Web Apps (React/Next.js)                          │
│  Azure CDN / Front Door                                          │
│  Azure AD B2C (auth — email + Google/Microsoft/Apple)           │
└──────────────────────────┬──────────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────────┐
│                        API LAYER                                 │
│  Azure API Management                                            │
│  Azure Functions (Node.js/Python — serverless)                  │
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
                  │                │
                  │ Azure AI       │
                  │ Video Indexer  │
                  │ (if video —    │
                  │  gestures,     │
                  │  scene detect) │
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
| **Static Web Apps** | Host React/Next.js frontend with built-in auth integration |
| **Azure AD B2C** | User auth — email signup + Google/Microsoft/Apple social login |
| **API Management** | API gateway, rate limiting, analytics |
| **Azure Functions** | Serverless API endpoints and processing logic |
| **Durable Functions** | Orchestrate the multi-step sermon analysis pipeline |
| **Blob Storage** | Store uploaded video/audio files |
| **Media Services** | Transcode video, extract audio track for speech processing |
| **AI Speech Service** | Transcription with speaker diarization, word-level timestamps |
| **Azure OpenAI (GPT-4)** | Sermon analysis, scoring, segment classification, commentary cross-reference |
| **AI Language Service** | Sentiment analysis, key phrase extraction, topic modeling |
| **AI Video Indexer** | Video-specific analysis (if video uploaded) — scene detection, visual cues |
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
User uploads video/audio (or pastes YouTube/Vimeo URL)
    │
    ▼
1. Azure Function: Validate upload, create sermon record in Cosmos DB (status: processing)
    │
    ▼
2. If YouTube/Vimeo URL → Azure Function: Download via yt-dlp, store in Blob Storage
   If direct upload → Store in Blob Storage
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
  "sourceUrl": "https://youtube.com/watch?v=...",
  "status": "complete",
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
| **Upload** | Drag-and-drop video/audio or paste YouTube/Vimeo URL. Tag pastor name, church, denomination, date |
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

## MVP Scope (Phase 1)

### In Scope
- User signup (email + social login via Azure AD B2C)
- Upload video/audio (direct + YouTube URL)
- Transcription via Azure AI Speech
- Segment classification via Azure OpenAI
- Scripture detection and basic verification
- PSR scoring (all 8 categories + composite)
- Sermon detail page with full scorecard
- Pastor profile with trend tracking
- Basic search
- Leaderboards (top PSR, most improved)
- Follow pastors, create playlists
- Pastor profile claiming
- English only
- Up to 2 hours sermon length

### Out of Scope (Future Phases)
- Monetization / premium tiers
- Multi-language support
- Mobile native apps (web-responsive only for MVP)
- Comments/discussion
- Video-specific analysis (gestures, eye contact via Video Indexer)
- Real-time live sermon scoring
- Church organization accounts
- API for third-party integrations
- Sermon comparison (side-by-side two sermons)

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
| Frontend | React or Next.js, TypeScript, Tailwind CSS |
| Auth | Azure AD B2C |
| API | Azure Functions (Python or Node.js) |
| Orchestration | Azure Durable Functions |
| Database | Azure Cosmos DB (NoSQL) |
| Search | Azure AI Search |
| Cache | Azure Cache for Redis |
| Storage | Azure Blob Storage |
| AI - Speech | Azure AI Speech Service |
| AI - Language | Azure AI Language Service |
| AI - LLM | Azure OpenAI (GPT-4) |
| AI - Video | Azure AI Video Indexer (Phase 2) |
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
| Blob Storage | ~$5 (depending on uploads) |
| AI Speech | ~$1/hr of audio transcribed |
| Azure OpenAI | ~$0.01-0.03 per 1K tokens |
| AI Search | ~$75 (basic tier) |
| Redis Cache | ~$15 (basic) |
| Service Bus | ~$10 (basic) |
| AD B2C | Free up to 50K MAU |
| **Total estimate** | **~$150-300/mo at low volume** |

*Costs scale with usage — primarily driven by sermon processing (Speech + OpenAI tokens).*

---

## Next Steps

1. Set up Azure resource group and DevOps project
2. Create Bicep templates for core infrastructure
3. Build upload → transcribe → store pipeline (minimal viable pipeline)
4. Build PSR scoring engine with Azure OpenAI
5. Build frontend with sermon detail page
6. Add pastor profiles and leaderboards
7. Add scripture verification with commentary corpus
8. Polish, test, deploy to production
