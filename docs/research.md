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
