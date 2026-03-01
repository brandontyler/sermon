# Research — Competitive Landscape, POCs, and Open-Source Tools

Extracted from sermonplan.md to keep the main plan focused on what we're building next.

---

## Competitive Landscape & Inspiration

### What Already Exists

| Product | What It Does | How PSR Is Different |
|---------|-------------|---------------------|
| **Chronicle.church** ($12-35/mo) | Upload sermon audio → AI transcription, summaries, themes, discussion questions, verse detection. Aimed at pastors archiving their own sermons. No scoring. | PSR *scores* sermons with a public composite rating. Chronicle is a private study tool; PSR is a public leaderboard. |
| **Logos Sermon Analyzer** (coming soon) | Upload recording → emotional arc, pacing metrics, vocal dynamics, coaching feedback. Part of the Logos Bible software ecosystem. | Similar analytics but no public profiles, no cross-pastor comparison, no composite score. Logos is a pastor's private tool. |
| **SermonAI / SermonDone** | AI sermon *preparation* tools — help pastors write sermons, generate outlines, create social clips. | These help *create* sermons. PSR *evaluates* them after delivery. Completely different use case. |
| **SermonAudio.com** | Massive sermon hosting platform (100K+ sermons). Has an API with speaker/topic/scripture indexes. No analysis or scoring. | SermonAudio is a distribution platform. PSR adds the analytics layer that SermonAudio doesn't have. |
| **Sermon Evaluation Forms** (paper/PDF) | Seminary rubrics and church feedback forms. Manual, subjective, small sample. Gordon-Conwell, Truett Seminary, and others publish rubrics. | PSR automates what seminaries do manually. Same categories (biblical fidelity, delivery, application) but AI-scored at scale. |

### Key Insight: Nobody Does Public Scoring

Every existing tool is either:
1. A **private pastor tool** (Chronicle, Logos) — pastor uploads their own sermon for self-improvement
2. A **preparation tool** (SermonAI) — helps write sermons, not evaluate them
3. A **hosting platform** (SermonAudio) — distribution without analysis
4. A **manual form** (seminary rubrics) — subjective, small scale, not public

**PSR's unique angle: public, data-driven, comparable scores across pastors.** Like Rotten Tomatoes for sermons or QBR for quarterbacks. Nobody is doing this.

### Creative Ideas from History & Academia

**1. The Seminary Rubric Approach (Digitized)**
Seminary homiletics classes have used structured rubrics for decades. Common dimensions:
- Exegesis/Theology (15 criteria, 1-5 scale) — is the text handled faithfully?
- Application — does it connect to real life?
- Presentation — delivery, eye contact, vocal variety
- Structure — intro hook, clear points, transitions, conclusion

PSR essentially automates this with AI. The Gordon-Conwell rubric and Truett Seminary survey are well-documented frameworks we can validate our categories against.

**2. The "Preaching Today" Screener Model**
Christianity Today's *Preaching Today* service had professional screeners who evaluated thousands of sermons for their subscription library. Their key finding: **"Most sermons are Scriptural, but many do not keep their finger on the text."** Listeners felt authority shift from Bible to preacher when scripture wasn't referenced frequently. This directly validates our "Time in the Word" and "Passage Focus" categories.

**3. The Four-Question Test (Glen Stanton)**
A beautifully simple framework: (1) Was Christ proclaimed clearly? (2) Was it biblically sound? (3) Was it interesting? (4) Did it ask me to do something? Four questions that map cleanly to our 8 categories. Could be a "quick score" summary view.

**4. Congregation Sentiment (Future Feature)**
Some churches use real-time audience response systems. Imagine: congregation members tap a "resonating" button during the sermon, creating a live engagement heatmap overlaid on the transcript. Crowdsourced + AI = powerful.

**5. Historical Preacher Benchmarking**
Compare modern sermons against the greats. Project Gutenberg has public domain sermons from Spurgeon (3,500+ sermons), Wesley, Edwards, Whitefield. Run them through PSR to create historical benchmarks. "Your sermon scored 78 — Spurgeon's average on Romans passages was 91." That's compelling.

**6. The "Sermon DNA" Fingerprint**
Every pastor has patterns — favorite illustrations, go-to scripture books, typical sermon length, filler word habits. Over time, PSR builds a "Sermon DNA" profile showing a pastor's signature style and how it evolves. Like a pitcher's pitch mix in baseball analytics.

### Free Data Sources (Confirmed Available)

| Source | Type | Access | Best For |
|--------|------|--------|----------|
| **SermonIndex API** (GitHub: sermonindex/audio_api) | 100K+ sermon metadata, organized by speaker/topic/scripture. Static JSON files. GPL-2.0 | Free, no auth | Building a sermon metadata corpus, speaker indexes, topic taxonomies |
| **Bible API** (bible-api.com) | Bible text, multiple translations | Free, no auth, JSON | Scripture reference verification in MVP |
| **API.Bible** (scripture.api.bible) | 2,500+ Bible versions, multiple languages | Free tier with API key | Multi-translation comparison |
| **ESV API** (api.esv.org) | ESV text | Free for non-commercial | High-quality English text |
| **OpenBible.info** | Cross-references, topical indexes, verse sentiment | Free | Cross-reference depth scoring |
| **Project Gutenberg** | Public domain sermon texts (Spurgeon, Wesley, Edwards, etc.) | Free, no restrictions | Historical benchmarking corpus |
| **BibleTalk.tv API** | Bible studies, verse data | Free JSON API | Supplementary verse context |
| **SermonScript.com** | Full sermon transcripts from well-known pastors | Free to read | Comparison corpus for scoring calibration |

---

## Proof of Concept #2: Scripture Cross-Reference Analyzer

### What It Does

Takes a sermon transcript (or the mock one from POC #1) and performs deep scripture analysis using **only free APIs** — no OpenAI key needed:

1. **Detect scripture references** in the transcript text using regex
2. **Fetch actual verse text** from Bible API (free, no auth)
3. **Fetch cross-references** from OpenBible.info
4. **Calculate metrics**: scripture density, cross-reference depth, time-in-word estimate
5. **Compare against a Spurgeon sermon** from Project Gutenberg as a historical benchmark

### Why This POC

- Proves the scripture detection + verification pipeline works with free tools
- Zero cost — no API keys needed at all
- Demonstrates the "historical benchmarking" idea
- Produces real, interesting data that's demo-worthy
- Complements POC #1 (which proved AI scoring) with a deterministic analysis layer

### How to Run

```bash
python3 poc/scripture_analyzer.py              # Analyze mock sermon
python3 poc/scripture_analyzer.py --compare    # Also compare against Spurgeon
```

### Output

`poc/scripture_analysis.json` — scripture references found, verse text fetched, cross-references, density metrics, and optional historical comparison.

---

## Open-Source Analysis Tools (Supplement to Azure Services)

These Python libraries run alongside Azure services to give us metrics that cloud APIs don't provide out of the box. **textstat and Parselmouth are included in MVP** (proven in POC #3, trivial to add). Others are Phase 1+.

### ⭐ Top Picks for PSR

| Tool | `pip install` | What It Does for Us | PSR Category |
|------|--------------|---------------------|-------------|
| **CrisperWhisper** ⭐ | github: `nyrahealth/CrisperWhisper` | Catches every "um", "uh", stutter, false start with timestamps. Standard Whisper/Azure Speech skip these | Delivery |
| **Parselmouth** ⭐ | `praat-parselmouth` | Pitch contour + loudness over time from audio. Detects monotone stretches, energy shifts, strategic vs hesitation pauses | Engagement, Delivery, Emotional Range |
| **textstat** ⭐ | `textstat` | Readability grade level (Flesch-Kincaid, etc.) in one call. Is the sermon accessible or PhD-level? | Clarity |
| **spaCy** ⭐ | `spacy` | NLP foundation — sentence parsing, POS tagging, imperative detection ("Go and do...") for Application scoring | Clarity, Application |
| **pythonbible** | `pythonbible` | Robust scripture reference parsing — handles abbreviations, ranges, multi-verse spans. Better than regex | Biblical Accuracy |
| **SpeechBrain SER** | `speechbrain` | Emotion classification from audio (not text). Segment sermon into chunks → plot emotional arc | Emotional Range |

### Key Idea

Feed GPT-4 pre-computed metrics (pitch variance, readability grade, filler count, coherence score) instead of asking it to infer everything from raw text. More consistent, reproducible scores — the LLM becomes a *scorer* that weighs measurements, not a *measurer* that guesses.

---

## Proof of Concept #3: Open-Source Audio + Text Analysis (Real Sermon)

### What We Did

Ran John Piper's "The Mighty and Merciful Message of Romans 1-8" (Sept 22, 2002, ~40 min, from desiringgod.org) through four open-source tools — zero API keys, everything local on a laptop CPU.

### How to Run

```bash
source .venv/bin/activate
python poc/audio_analysis_poc.py poc/samples/piper_romans_1_8.mp3
python poc/audio_analysis_poc.py poc/samples/piper_romans_1_8.mp3 --skip-transcribe  # reuse cached transcript
```

(Audio file not committed — download from desiringgod.org into `poc/samples/`)

### Results: Piper Benchmark

| Metric | Value | What It Means |
|--------|-------|---------------|
| Duration | 39.7 min | — |
| Words | 5,161 | — |
| WPM | 130 | Deliberate pace (avg conversational = 140-160) |
| Filler words | 59 (1.5/min) | Very clean. 43 of 59 are "so" (transitional, not hesitation) |
| Pitch mean | 172.8 Hz | Male vocal range |
| Pitch std | 61.1 Hz | Very expressive (monotone speaker ≈ 15-20 Hz) |
| Pitch range | 509.5 Hz | Huge — deep rumble to intense peaks |
| Volume range | 79.8 dB | Whisper to shout — uses volume as emphasis |
| Pauses | 805 (20.3/min) | Signature Piper — dramatic silence for emphasis |
| Flesch Reading Ease | 75.0 | Fairly easy — accessible to general audience |
| Grade Level | 7.1 | 7th grade. Deep theology in simple language |
| Scripture refs | 9 (0.23/min) | Overview sermon covering 8 chapters, so breadth over depth |
| Imperatives | 15 | Solid application — "I want you to..." moments |

### Hypothetical PSR Score: 84/100

| Category (Weight) | Score | Reasoning |
|--------------------|-------|-----------|
| Biblical Accuracy (25%) | 88 | 9 refs correctly placed, walking through Romans in order |
| Time in the Word (20%) | 75 | Covering 8 chapters in 40 min — breadth over depth by design |
| Passage Focus (10%) | 70 | Survey sermon, not single-passage exposition. Stays in Romans but jumps around |
| Clarity (10%) | 92 | 7th grade reading level with deep theology. Elite |
| Engagement (10%) | 95 | 61 Hz pitch variation + 80 dB volume range + 20 pauses/min. Data screams dynamic |
| Application (10%) | 82 | 15 imperative sentences — calling people to action, not just teaching |
| Delivery (10%) | 85 | 1.5 fillers/min is clean. 130 WPM is deliberate and controlled |
| Emotional Range (5%) | 90 | 509 Hz pitch range + volume dynamics = quiet intensity to full passion |

### Lessons Learned

1. **faster-whisper on CPU works** — transcribed 40 min in reasonable time, no GPU needed. Good enough for MVP
2. **Whisper skips filler words** — "so", "like", "right" are caught by text search, but true disfluencies ("um", "uh") are often omitted. CrisperWhisper would fix this — our filler count of 59 is likely an undercount
3. **Spoken scripture is hard to detect** — Piper says "chapter 3 verse 21" without repeating "Romans" every time. We had to build a contextual resolver that tracks the last-mentioned book. Edge case: "Revelation" appearing earlier caused one misattribution (tagged "Revelation 3:28" instead of "Romans 3:28"). `pythonbible` library would help here
4. **Parselmouth is the MVP audio tool** — pitch + intensity in 3 lines of code. Gives us Engagement and Delivery metrics that no text-only analysis can provide
5. **textstat is trivially easy** — one pip install, one function call, instant readability scores. No reason not to include this in MVP
6. **Piper makes a great benchmark** — 84 PSR feels right for an overview sermon from an elite preacher. A deep single-passage exposition from him would likely score 88-90. Good calibration target
7. **"so" as a filler is debatable** — 43 of 59 fillers were "so". It's more of a transition word for Piper. May need to weight true hesitation fillers (um, uh) differently from transitional fillers (so, right, you know)
8. **Pause detection needs refinement** — 805 pauses at 20/min seems high. The intensity-threshold approach catches both intentional dramatic pauses and natural breathing gaps. Need to distinguish strategic pauses (>1s) from micro-pauses (<0.3s)

---

## Proof of Concept #4 — Sermon Type Comparison (4 Piper Sermons)

Ran 4 Piper sermons through the POC #3 pipeline to test scoring bias across sermon types. Code: `poc/sermon_comparison.py`, results: `poc/sermon_comparison_results.json`.

**Sermons tested:**
| Sermon | Type | Passage | Duration |
|--------|------|---------|----------|
| The Mighty and Merciful Message of Romans 1-8 | Survey | Romans 1-8 overview | 39.7 min |
| Called According to His Purpose | Expository | Romans 8:28-30 | 35.0 min |
| Don't Waste Your Life (MSU) | Topical | Various | 56.4 min |
| No One Will Take Your Joy from You | Topical (pillar) | John 16:16-24 | 49.8 min |

**Key findings:**

1. **Sermon type bias confirmed.** Scripture density: expository 1.37/min, survey 0.91/min, topical 0.30-0.42/min. Same preacher, 3-4x gap based purely on structure.
2. **Regex scripture detection fails on whisper transcripts.** Detected 2 refs in the expository sermon; manual count found ~48. Whisper outputs "Romans 828" for "Romans 8:28", "Philippians 120" for "Philippians 1:20", etc.
3. **LLM analysis is strictly better than NLP heuristics for text metrics.** textstat gave -38.0 Flesch score on one transcript (nonsensical). spaCy found 2 imperatives in a 56-min talk full of application. An LLM would handle both correctly.
4. **Audio-level analysis (Parselmouth) still works well.** Pitch, intensity, and pause detection are reliable and not something an LLM can do. Keep Parselmouth for audio metrics, use LLM for everything text-based.
5. **Delivery varies by context.** University talk had more fillers (2.1/min) and less pitch variation than pulpit sermons. Expository had most pauses (35.9/min) — deliberate exposition, not a weakness.

**Decision: production pipeline = Parselmouth for audio + GPT-4 for all text analysis.** NLP heuristics (textstat, spaCy, regex scripture detection) are dropped.

---

## LLM Evaluation Strategy: Single-Pass vs Multi-Pass

With GPT-4 handling all text analysis (confirmed in POC #4), the question becomes: one massive prompt or multiple focused prompts?

**Single pass** (one prompt, all 8 categories): cheaper and faster, but accuracy degrades as the model juggles too many tasks. Scores tend to cluster toward the middle.

**Multi-pass** (one prompt per category): each prompt is focused and debuggable, but 8x the cost and latency.

**Decision: hybrid — 3 parallel passes grouped by shared context.**

| Pass | Categories | Why Grouped |
|------|-----------|-------------|
| **Pass 1: Biblical Analysis** | Biblical Accuracy, Time in the Word, Passage Focus | All require scripture detection + verification — same context |
| **Pass 2: Structure & Content** | Clarity, Application, Engagement | All about sermon structure and rhetorical quality |
| **Pass 3: Delivery** | Delivery, Emotional Range | Lean heavily on Parselmouth audio data (pitch, pauses, volume) rather than transcript text |

**Why this works:**
- 3 parallel API calls instead of 8 sequential — latency ≈ single pass via Durable Functions fan-out
- Each pass has a tight, focused prompt — better accuracy than one overloaded prompt
- Categories sharing context (scripture refs, audio metrics) are co-located
- Individual passes can be iterated/calibrated without breaking others

**Sermon type normalization** (expository/topical/survey) happens *after* all passes return, as a separate lightweight step adjusting raw scores. Keeps evaluation passes clean and normalization logic in one place.

---

## Proof of Concept #5 — Azure Multi-Model Pipeline (Real Azure Services)

### What We Did

Ran Piper's "Called According to His Purpose" (Romans 8:28-30, ~35 min) through the full production-mirror pipeline using real Azure services: Azure AI Speech for transcription, Parselmouth for audio metrics, and 3 parallel LLM passes with task-appropriate models.

Code: `poc/azure_multipass_poc.py`, results: `poc/multipass_result_piper_called_according_to_his_purpose.json`.

### Models Used & Timing

| Pass | Model | Time | Task |
|------|-------|------|------|
| Pass 1: Biblical | o4-mini | 10.1s | Scripture verification, accuracy, passage focus |
| Pass 2: Structure | GPT-4.1 | 6.8s | Clarity, application, engagement |
| Pass 3: Delivery | GPT-4.1-mini | 5.1s | Delivery + emotional range (interprets Parselmouth data) |
| Classification | GPT-4.1-mini | 1.0s | Expository/topical/survey |

All 4 calls ran in parallel — **10s wall-clock** vs ~23s sequential.

### Results: PSR Scorecard

**Composite PSR: 82.7/100** | Sermon Type: Expository (90% confidence)

| Category | Score | Weight |
|----------|-------|--------|
| Biblical Accuracy | 95 | 25% |
| Time in the Word | 70 | 20% |
| Passage Focus | 90 | 10% |
| Clarity | 82 | 10% |
| Application | 68 | 10% |
| Engagement | 89 | 10% |
| Delivery | 75 | 10% |
| Emotional Range | 90 | 5% |

### Key Findings

1. **o4-mini scripture detection is dramatically better than regex.** Found 6 refs (Romans 8:28-30, 35-37), all verified in context. POC #4's regex found only 2 refs on the same sermon's Whisper transcript. Reasoning model correctly evaluates "is this quote used in context?" — validates the o4-mini choice for Pass 1.

2. **Application scoring (68) is the most telling result.** Piper is heavy on theology and wonder, lighter on concrete "here's your homework" moments. The model identified takeaways ("find refuge in Romans 8:28", "let your faith become strong") but correctly flagged them as abstract rather than actionable. This is exactly the nuance we want PSR to surface.

3. **Parallel execution delivers.** 3 passes + classification in 10s wall-clock. The Durable Functions fan-out/fan-in architecture maps directly to this pattern.

4. **Sermon type classification works.** 90% confidence expository — "focuses deeply on Romans 8:28-30, analyzing verses in detail verse-by-verse." No normalization adjustments needed for expository type.

5. **Parselmouth + LLM combo validated.** Pitch std 74.6Hz, range 524Hz, intensity range 119dB — the delivery model used these objective measurements to score emotional range (90) with specific reasoning about vocal dynamics. Text-only analysis couldn't produce this.

### ⚠️ Known Issue: WPM Calculation Bug

POC #5 reported **30.4 WPM** — clearly wrong. POC #4 measured the same sermon at **108.4 WPM** via local Whisper. The Azure Speech transcript only captured **1,064 words** vs POC #4's **3,794 words** for the same audio.

**Root cause:** Azure Speech chunking (5-min segments with ffmpeg splitting) likely dropped audio between chunks or had session timeout issues. The continuous recognition callback pattern may miss segments at chunk boundaries.

**Impact:** WPM and word count are unreliable. All text-based scoring (biblical, structure) operated on a partial transcript, meaning scores may shift with a complete transcript. Audio metrics (Parselmouth) are unaffected since they process the full audio file directly.

**Fix needed for production:**
- Use Azure AI Speech batch transcription API instead of real-time chunking — handles long files natively without manual splitting
- Or use continuous recognition on the full file with proper session management
- Add a word count sanity check: flag if WPM < 80 or > 200 as likely transcription error

### Comparison: Same Sermon Across POCs

| Metric | POC #4 (Whisper + regex) | POC #5 (Azure Speech + multi-model) |
|--------|--------------------------|--------------------------------------|
| Words transcribed | 3,794 | 1,064 (⚠️ partial) |
| WPM | 108.4 | 30.4 (⚠️ bug) |
| Scripture refs found | 2 (regex) | 6 (o4-mini reasoning) |
| Filler words | 36 | 0 (Azure Speech also skips fillers) |
| Composite PSR | N/A (no scoring) | 82.7 |

---

## Proof of Concept #6 — Azure Fast Transcription API

### What We Did

Tested the Azure AI Speech fast transcription API as a fix for POC #5's word loss issue. The fast transcription API is synchronous (no polling), handles files up to 2 hours / 300MB, and uploads audio directly via multipart form data — no blob storage needed.

Code: `poc/azure_fast_transcription_poc.py`, results: `poc/fast_transcription_result_piper_called_according_to_his_purpose.json`.

### Results

| Metric | POC #4 (Whisper) | POC #5 (RT chunk) | POC #6 (Fast API) |
|--------|-----------------|-------------------|-------------------|
| Words | 3,794 | 1,064 ⚠️ | **3,762** ✓ |
| WPM | 108.4 | 30.4 ⚠️ | **107.5** ✓ |
| Scripture refs (regex) | 2 | N/A | **25** |
| Transcription time | ~120s | ~60s | **44s** |

- **Word count**: 3,762 vs POC #4's 3,794 — 99.2% match. Word loss problem solved.
- **Speed**: 44s for 35 min of audio = 47x faster than real-time.
- **Scripture formatting**: "Romans 8:28", "Romans 8:29", "Romans 9:11" — all properly formatted with colons. Regex alone found 25 refs vs POC #4's 2 from Whisper's mangled output.
- **WPM sanity check**: 107.5 WPM — passes the 80-200 range check.
- **Transcript quality**: Excellent. Opens with "The morning text for today's sermon is Romans 8:28-30. We know that in everything God works for good with those who love Him..."

### Decision: Fast Transcription API for Production

The fast transcription API replaces both real-time chunking (POC #5) and the batch API in our pipeline:
- No blob storage needed (uploads directly)
- Synchronous (no polling/queue time)
- Supports files up to 2 hours / 300MB (covers MVP max of 1 hour)
- Word-level timestamps included
- Diarization available
- 47x faster than real-time

**Tradeoff**: Fast transcription costs $1.00/hour (same as real-time), vs batch API at $0.36/hour. For MVP volume this is negligible. At scale, we can switch to batch if cost matters more than latency.

---

## Proof of Concept #7 — Validated Multipass Scoring (Full Transcript)

### What We Did

Re-ran POC #5's 3-pass scoring pipeline on POC #6's complete transcript (3,762 words vs 1,064). Same models, same prompts, same Parselmouth data — only the transcript changed. This validates whether the 82.7 composite from POC #5 was accurate or distorted by the partial transcript.

Code: `poc/validated_multipass_poc.py`, results: `poc/validated_multipass_result_piper_called_according_to_his_purpose.json`.

### Results: Score Comparison

**Composite PSR: 88.0/100** (POC #5: 82.7 | Δ +5.3)

| Category | POC #7 (3,762 words) | POC #5 (1,064 words) | Delta |
|----------|---------------------|---------------------|-------|
| Biblical Accuracy | 95 | 95 | 0 |
| Time in the Word | 80 | 70 | +10 |
| Passage Focus | 85 | 90 | -5 |
| Clarity | 92 | 82 | +10 |
| Application | 81 | 68 | +13 |
| Engagement | 95 | 89 | +6 |
| Delivery | 85 | 75 | +10 |
| Emotional Range | 90 | 90 | 0 |

Scripture refs found: 12 (POC #5: 6). All 12 used in context, 0 out of context.

### Key Findings

1. **Partial transcript underestimated by 5.3 points.** The composite jumped from 82.7 → 88.0. Not catastrophic, but meaningful — the difference between "good" and "excellent" in any scoring system.

2. **Application saw the biggest swing (+13).** With the full transcript, the model found 7 application moments vs 3 in POC #5. Piper's application is woven throughout — you need the whole sermon to see it. This confirms that text-based categories are sensitive to transcript completeness.

3. **Biblical Accuracy and Emotional Range were stable (Δ 0).** Biblical Accuracy was already high because o4-mini found the key refs even in the partial text. Emotional Range relies heavily on Parselmouth audio data, which was identical. These categories are robust to transcript quality.

4. **Passage Focus dropped slightly (-5).** More text revealed more tangents (4 vs 1). The construction site illustration, dog analogy, Billy Graham mention, and straw-house metaphor were all visible in the full transcript. This is actually a more accurate score — the partial transcript made the sermon look more focused than it was.

5. **o4-mini found 2x more scripture refs (12 vs 6).** Full transcript revealed Deuteronomy 30:6, 1 Corinthians 1:23-24, and Romans 9:10-12 — all cross-references Piper uses to build his argument. These were in the 72% of text that POC #5 never saw.

6. **Delivery jumped +10 with correct WPM.** POC #5 fed the model 30.4 WPM (broken), POC #7 fed 107.5 WPM (correct). The model correctly assessed this as "measured, thoughtful delivery suited to deep theological exposition" instead of "extremely slow."

7. **88.0 feels right for this sermon.** Piper preaching a focused expository sermon on Romans 8:28-30 — strong biblical grounding, excellent engagement, slightly abstract application. The POC #3 hypothetical estimate was 84 for a survey sermon; this expository sermon scoring 88 is consistent.

### Cost

~$0.09 (OpenAI only — reused cached transcript and Parselmouth data). Total project spend: $0.18.

### Conclusion

**Always score on complete transcripts.** The fast transcription API (POC #6) must run before scoring. The pipeline architecture already assumes this (transcribe → score), so no design change needed — but this POC proves why that ordering is non-negotiable.

---

## Cost Analysis (All POC Runs)

### What We've Spent

| Service | Usage | Cost |
|---------|-------|------|
| Azure Speech (real-time + fast) | 1.2 hours total (3 POC runs) | **$0.00** (free tier: 5 hrs/mo) |
| Azure OpenAI (POC #5 basic, GPT-4o) | ~1K tokens | $0.01 |
| Azure OpenAI (POC #5 multipass, 4 calls) | ~42K tokens | $0.09 |
| **Total spent to date** | | **$0.09** |

### Per-Sermon Cost Breakdown (Production Estimate, 40-min avg sermon)

| Component | Fast Transcription | Batch Alternative |
|-----------|-------------------|-------------------|
| Azure Speech | $0.67 ($1.00/hr) | $0.24 ($0.36/hr) |
| Pass 1: o4-mini (biblical) | $0.03 | $0.03 |
| Pass 2: GPT-4.1 (structure) | $0.05 | $0.05 |
| Pass 3: GPT-4.1-mini (delivery) | $0.01 | $0.01 |
| Classification: GPT-4.1-mini | $0.005 | $0.005 |
| **Total per sermon** | **$0.75** | **$0.33** |

**Key insight**: Speech transcription is now the dominant cost (89% with fast API), not OpenAI (11%). The original $0.08/sermon estimate only counted OpenAI tokens — it didn't include transcription cost.

### Monthly Projections

| Sermons/month | Fast API | With free tier (5 hrs) | Batch alternative |
|---------------|----------|----------------------|-------------------|
| 10 | $7.53 | $2.53 | $3.30 |
| 50 | $37.65 | $32.65 | $16.50 |
| 100 | $75.31 | $70.31 | $33.00 |

### Pricing Decision for MVP

Use **fast transcription** ($1.00/hr) for MVP. Reasons:
- Simpler architecture (synchronous, no blob storage, no polling)
- 5 free hours/month covers ~7 sermons during development
- At MVP volume (<50 sermons/mo), the $20 difference vs batch isn't worth the added complexity
- Can switch to batch API later if cost optimization needed at scale

---

## Beginner's Guide: How the Pipeline Works (Step by Step)

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

## Azure OpenAI Model Selection Research (July 2025)

Since PSR's scoring quality is almost entirely determined by the LLM, we researched the best available models on Azure for each specific task. The goal: use the best model for each job, not one-size-fits-all.

### Models Currently Available on Azure OpenAI

| Model | Type | Context Window | Pricing (per 1M tokens) | Key Strength |
|-------|------|---------------|------------------------|-------------|
| **GPT-4.1** | Non-reasoning | 1M tokens | $2.00 in / $8.00 out | Instruction following, structured output, long context |
| **GPT-4.1-mini** | Non-reasoning | 1M tokens | $0.40 in / $1.60 out | Same capabilities as 4.1 at 5x cheaper |
| **GPT-4.1-nano** | Non-reasoning | 1M tokens | Cheapest tier | Fast, lightweight classification tasks |
| **o3** | Reasoning | 200K tokens | $10.00 in / $40.00 out | Deep multi-step reasoning, tool use |
| **o4-mini** | Reasoning | 200K tokens | $1.10 in / $4.40 out | Near-o3 reasoning at ~9x cheaper, strong on structured eval |
| **GPT-4o** | Non-reasoning | 128K tokens | $2.50 in / $10.00 out | Previous gen, still solid but superseded by 4.1 |

GPT-5 series models are also on Azure but require registration/approval and are significantly more expensive. Not needed for MVP.

### Recommended Model Per PSR Task

| Task | Recommended Model | Why |
|------|------------------|-----|
| **Pass 1: Biblical Analysis** (Accuracy, Time in Word, Passage Focus) | **o4-mini** | Scripture verification requires reasoning — "is this quote in context?" needs chain-of-thought. o4-mini gives o3-level reasoning at 9x less cost. |
| **Pass 2: Structure & Content** (Clarity, Application, Engagement) | **GPT-4.1** | Instruction following is the key skill here. GPT-4.1 excels at following complex rubrics and returning structured JSON. No deep reasoning needed — it's pattern matching against criteria. |
| **Pass 3: Delivery** (Delivery, Emotional Range) | **GPT-4.1-mini** | This pass mostly interprets pre-computed Parselmouth data (pitch, pauses, volume). The heavy lifting is already done — the LLM just needs to score against thresholds. Cheapest model that handles structured output well. |
| **Sermon Type Classification** | **GPT-4.1-nano** | Simple classification (expository/topical/survey). Lightweight task, cheapest model. |
| **Segment Classification** | **GPT-4.1-mini** | Classifying transcript segments (scripture, teaching, anecdote, application). Moderate complexity, good instruction following needed. |
| **Score Normalization** | **Code (no LLM)** | Pure math — adjust raw scores by sermon type. No LLM needed. |

### Why Not One Model For Everything?

- **o3** ($10/$40 per 1M tokens) is overkill for tasks that don't need deep reasoning. Using it for delivery scoring would be like hiring a PhD to count filler words.
- **GPT-4.1** ($2/$8) is the sweet spot for structured evaluation — it scores 45.1% on hard instruction evals vs GPT-4o's lower marks, and has a 1M token context window.
- **o4-mini** ($1.10/$4.40) is the secret weapon — reasoning capability close to o3 but priced near GPT-4.1-mini. Perfect for biblical analysis where the model needs to actually *think* about whether a scripture reference is used in context.
- **GPT-4.1-mini** ($0.40/$1.60) handles structured output well for simpler evaluation tasks. 5x cheaper than full 4.1.

### Estimated Cost Per Sermon (Updated)

A typical sermon transcript is ~5K-7K words (~7K-10K tokens). With 3 parallel passes:

| Pass | Model | Est. Input Tokens | Est. Output Tokens | Cost |
|------|-------|------------------|-------------------|------|
| Pass 1 (Biblical) | o4-mini | ~12K | ~3K | ~$0.026 |
| Pass 2 (Structure) | GPT-4.1 | ~12K | ~3K | ~$0.048 |
| Pass 3 (Delivery) | GPT-4.1-mini | ~10K | ~2K | ~$0.007 |
| Classification | GPT-4.1-nano | ~8K | ~1K | ~$0.002 |
| **Total** | | | | **~$0.08** |

Down from the original ~$0.10-0.30 estimate with GPT-4o for everything. Better models, lower cost.

### Region Availability

All recommended models (GPT-4.1, GPT-4.1-mini, GPT-4.1-nano, o4-mini) are available via Global Standard deployment in East US, East US 2, and most other US regions. No availability concerns for MVP.

### Key Takeaway

The "one model fits all" era is over. Using task-appropriate models gives us better accuracy on reasoning-heavy tasks (biblical analysis) while cutting costs on simpler tasks (delivery scoring, classification). The 3-pass architecture maps cleanly to 3 different model tiers.