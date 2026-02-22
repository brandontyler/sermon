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

## MVP Scope (Phase 1)

### In Scope
- User signup (email + social login via Azure AD B2C)
- Direct upload of video/audio files (MP3, MP4, WAV, M4A, WEBM — max 2 hours / 2GB)
- Transcription via Azure AI Speech
- Segment classification via Azure OpenAI
- Scripture detection and basic verification (denomination-aware)
- PSR scoring (all 8 categories + composite)
- Sermon detail page with full scorecard
- Pastor profile with trend tracking
- Basic search
- Leaderboards (top PSR, most improved)
- Follow pastors, create playlists
- Pastor profile claiming
- Content moderation (automated + manual review queue)
- Pastor opt-out / removal request workflow
- English only
- Up to 2 hours sermon length

### Out of Scope (Future Phases)
- Monetization / premium tiers
- YouTube/Vimeo URL import (legal risk — ToS prohibit downloading)
- Multi-language support
- Mobile native apps (web-responsive only for MVP)
- Comments/discussion
- Video-specific analysis (gestures, eye contact via Video Indexer)
- Real-time live sermon scoring
- Church organization accounts
- API for third-party integrations
- Sermon comparison (side-by-side two sermons)

---

## Content Moderation

### Automated Checks (on upload)

- **File validation** — Verify file type, duration (max 2 hours), file size (max 2GB)
- **Audio content check** — After transcription, run a classification pass to verify the content is a sermon/religious talk (not music, podcasts, random audio, or abusive content)
- **Duplicate detection** — Hash-based check to prevent the same file from being uploaded twice
- **Rate limiting** — Max 5 uploads per user per day to prevent spam

### Manual Review Queue

- Uploads flagged by automated checks go to a moderation queue
- Admin dashboard to approve, reject, or remove content
- Rejection reasons: not a sermon, copyrighted content, abusive/spam, duplicate

### Reporting

- Users can flag/report any sermon for review
- Report reasons: not a sermon, incorrect attribution, copyrighted, offensive
- Reports trigger manual review

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

## Next Steps

### Phase 0.5 — Core Pipeline (validate the PSR concept)
1. Set up Azure resource group and DevOps project
2. Create Bicep templates for core infrastructure (Functions, Blob, Cosmos, Speech, OpenAI)
3. Build upload → transcribe → store pipeline (minimal viable pipeline)
4. Build PSR scoring engine with Azure OpenAI (all 8 categories)
5. **Prototype Biblical Accuracy in isolation** — build the commentary corpus RAG, test denomination-aware verification against sample sermons, iterate on scoring calibration before integrating
6. Build frontend: upload page + sermon detail page with full scorecard

### Phase 1 — MVP (public launch)
7. Add pastor profiles, claiming workflow, and opt-out mechanism
8. Add leaderboards and basic search
9. Add content moderation pipeline (automated checks + admin review queue)
10. Add user features: follow pastors, playlists, account page
11. Polish, test, deploy to production

### Phase 2 — Growth
12. Semantic/vector search upgrade (AI Search S1)
13. Video-specific analysis (Video Indexer)
14. Multi-language support
15. Church organization accounts
16. Sermon comparison (side-by-side)
