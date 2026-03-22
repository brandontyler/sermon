"""LLM scoring passes, classification, and summary generation."""

from activities.helpers import _openai_client, log


def pass1_biblical(input_data):
    """Pass 1: Biblical Analysis via o4-mini."""
    client = _openai_client()
    transcript = input_data["transcript"]

    from openai import BadRequestError
    try:
        resp = client.chat.completions.create(
            model="o4-mini",
            response_format={"type": "json_object"},
            messages=[{"role": "user", "content": f"""You are a biblical scholarship engine analyzing a sermon transcript. Return JSON with:

- "biblical_accuracy": {{"score": 0-100, "scripture_refs_found": [list of "Book Chapter:Verse" references detected], "refs_used_in_context": count, "refs_out_of_context": count, "reasoning": "..."}}
- "time_in_the_word": {{"score": 0-100, "biblical_content_pct": estimated %, "direct_quotation_pct": estimated %, "anecdote_pct": estimated %, "reasoning": "..."}}
  IMPORTANT: "Time in the Word" measures BIBLICAL CONTENT DENSITY — not just direct quotation. Score based on how much is grounded in biblical truth (quoted, taught, applied, exposited) vs secular content. 90-100=nearly all biblical, 70-89=majority, 50-69=mix, 30-49=more illustration, 0-29=minimal.
- "passage_focus": {{"score": 0-100, "main_passage": "...", "time_on_main_passage_pct": %, "tangent_count": int, "reasoning": "..."}}

PASSAGE FOCUS — CONDITIONAL RUBRIC:
  First determine: is this sermon single-passage (expository) or multi-passage (topical/thematic)?
  FOR SINGLE-PASSAGE SERMONS: Score based on depth and time spent on the announced/main passage.
    85-95: Deep verse-by-verse exposition, rarely leaves the passage
    70-84: Solid time on main passage with brief supporting references
    50-69: Announced a passage but spent significant time elsewhere
    15-49: Announced a passage then mostly abandoned it
    0-14: No identifiable main passage or completely ignored it
  FOR MULTI-PASSAGE SERMONS: Score based on "Scriptural Integration" — are the multiple passages handled faithfully and do they support a unified biblical thesis?
    85-95: Multiple passages, each EXEGETED in context (not just quoted), building a coherent biblical argument with clear textual connections between passages
    70-84: Most passages are explained in context with a clear unifying biblical theme; minor proof-texting on 1-2 supporting verses is acceptable
    55-69: Theme is biblical but passages are handled superficially — quoted or paraphrased without exegesis, used as springboards for stories rather than taught
    40-54: Passages are referenced but function as decoration — the sermon could make the same points without them
    15-39: Passages feel random, no unifying biblical thesis, or most are proof-texted
    0-14: No clear scriptural basis for the theme
  CRITICAL: Touching a verse then immediately pivoting to a personal story or motivational point = superficial handling (55-69 range). The passage must be TAUGHT, not just CITED.

SCORING SCALE — use the FULL 0-100 range, not just 40-90:
  0-15:  Harmful — fabricated scripture, heretical claims, dangerous theology
  15-30: Poor — out-of-context proof-texting, scripture used as decoration, no real exegesis
  30-50: Below average — some biblical content but poorly handled or shallow
  50-70: Average — decent biblical grounding with some gaps
  70-85: Good — solid exegesis, faithful handling of text
  85-95: Excellent — seminary-quality exposition, deep and accurate
  95-100: Exceptional — historically significant (Spurgeon, Lloyd-Jones tier)

CALIBRATION EXAMPLES — FULL RANGE (do NOT cluster in 70-80):
  POOR (15-30):
  - Proof-texting Jeremiah 29:11 as a personal prosperity promise = Biblical Accuracy 15-25
  - Sermon is mostly anecdotes, pop culture, and personal stories with a few verses sprinkled in = Time in the Word 10-25
  - Announcing a passage then never teaching it = Passage Focus 5-15
  MID-RANGE (45-65) — most sermons should NOT score above this unless genuinely strong:
  - References 5-8 verses correctly but never goes deeper than surface reading = Biblical Accuracy 50-60
  - About half the sermon is biblical content, half is stories/illustrations = Time in the Word 45-55
  - Stays mostly on topic but makes 3-4 extended tangents = Passage Focus 50-60
  - Quotes scripture accurately but applies it generically without exegesis = Biblical Accuracy 55-65
  GOOD (70-85):
  - Solid exegesis of main passage with accurate cross-references = Biblical Accuracy 75-85
  - Majority of sermon grounded in biblical exposition with purposeful illustrations = Time in the Word 70-80
  EXCELLENT (85-95):
  - Deep verse-by-verse exposition with Greek/Hebrew word study = 85-95 across all three

METHODOLOGY: First list specific observations and evidence from the transcript, THEN derive scores from that evidence. Do not pick a score first and justify it afterward.

Be rigorous. Check whether each scripture reference is used in its proper context.

SERMON TRANSCRIPT:
{transcript}"""}],
    )
    except BadRequestError as e:
        if "content_filter" in str(e) or "content management policy" in str(e):
            log.warning("[pass1_biblical] Content filter triggered, returning fallback scores")
            from schema import CATEGORY_KEY_MAP
            fallback = {"score": 50, "reasoning": "Content filter triggered — fallback score. Manual review recommended."}
            return {CATEGORY_KEY_MAP[k]: fallback for k in ["biblical_accuracy", "time_in_the_word", "passage_focus"]}
        raise

    from schema import CATEGORY_KEY_MAP, validate_llm_response
    raw = validate_llm_response(resp.choices[0].message.content, {
        "biblical_accuracy": ["score", "reasoning"],
        "time_in_the_word": ["score", "reasoning"],
        "passage_focus": ["score", "reasoning"],
    })

    result = {}
    for snake_key in ["biblical_accuracy", "time_in_the_word", "passage_focus"]:
        camel_key = CATEGORY_KEY_MAP[snake_key]
        result[camel_key] = {"score": raw[snake_key]["score"], "reasoning": raw[snake_key]["reasoning"]}
    return result


def pass2_structure(input_data):
    """Pass 2: Structure & Content via GPT-5-mini."""
    client = _openai_client()
    transcript = input_data["transcript"]

    from openai import BadRequestError
    try:
        resp = client.chat.completions.create(
            model="gpt-5-mini",
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": """You are a sermon structure analyst. Evaluate against these rubrics and return JSON.

CLARITY (10%): Logical flow, clear transitions, identifiable structure, accessible language.
  KEY DISCRIMINATING QUESTIONS — answer these before scoring:
  - Could a listener state the single main point of this sermon? If not, score below 60.
  - Does each section clearly advance the argument, or do sections feel disconnected?
  - Are transitions explicit (speaker signals movement) or implicit (listener figures it out)?
  - Is there a clear introduction-body-conclusion arc?

APPLICATION (10%): Practical takeaways, "so what?" moments, imperative language, specificity.
  KEY DISCRIMINATING QUESTIONS:
  - Are applications SPECIFIC (name a concrete action, situation, or change) or VAGUE ("love more", "pray more", "trust God")?
  - Does the speaker connect biblical truth to the listener's actual Monday-through-Saturday life?
  - Vague platitudes ("just trust God more") = Application 30-45, not 65-75.

ENGAGEMENT (10%): Rhetorical variety, audience connection, illustration quality, content pacing.
  KEY DISCRIMINATING QUESTIONS:
  - Does the sermon create genuine tension that gets resolved, or is it flat throughout?
  - Are illustrations specific and culturally relevant, or generic and interchangeable?
  - Does the speaker demonstrate awareness of potential objections or counter-arguments?
  - A sermon where every illustration could be swapped into any other sermon = below 65.

SCORING SCALE — use the FULL 0-100 range, not just 70-85:
  0-15:  Incoherent — no structure, no application, no audience awareness
  15-30: Poor — rambling, loses place, vague platitudes instead of application
  30-50: Below average — some structure but disorganized, generic takeaways
  50-65: Average — identifiable points but transitions are abrupt, applications are vague, illustrations are generic
  65-75: Above average — clear structure with some gaps, decent but not compelling
  75-85: Good — clear structure, specific application, effective illustrations
  85-95: Excellent — masterful flow, compelling and specific, deeply engaging
  95-100: Exceptional — historically significant sermon craft

CALIBRATION EXAMPLES — MID-RANGE (most sermons land here):
  Clarity 50-60: Clear 3-point structure but transitions are abrupt, listener has to infer connections between sections
  Clarity 60-70: Identifiable structure with some explicit transitions, but the main point is buried or unclear
  Application 40-55: Applications exist but are vague ("love more", "pray more") without specificity about HOW or WHEN
  Application 55-70: Some specific applications mixed with generic ones; listener gets 1-2 concrete takeaways
  Engagement 45-60: Good rhetorical questions but no tension/resolution arc, predictable pacing, generic illustrations
  Engagement 60-70: Some effective moments but overall flat — no sustained narrative arc or compelling build

CALIBRATION EXAMPLES — EXTREMES:
  Poor: "Just be positive" / "trust the process" as application = Application 10-20
  Poor: No identifiable structure, speaker loses place, random tangents = Clarity 15-25
  Poor: Being funny/relatable does NOT rescue a sermon with no structure or substance — Engagement 25-40
  Excellent: Masterful rhetorical arc with specific, culturally relevant illustrations that serve the text = Engagement 85-95

METHODOLOGY: First list specific observations from the transcript, THEN derive scores. Do not pick a score first."""},
            {"role": "user", "content": f"""Evaluate this sermon transcript:

{transcript}

Return JSON:
- "clarity": {{"score": 0-100, "structure_points": [main points], "transition_quality": "strong/moderate/weak", "reasoning": "..."}}
- "application": {{"score": 0-100, "actionable_takeaways": [list], "application_moments": count, "reasoning": "..."}}
- "engagement": {{"score": 0-100, "rhetorical_devices": [list], "audience_connection": "strong/moderate/weak", "reasoning": "..."}}"""},
        ],
    )
    except BadRequestError as e:
        if "content_filter" in str(e) or "content management policy" in str(e):
            log.warning("[pass2_structure] Content filter triggered, returning fallback scores")
            from schema import CATEGORY_KEY_MAP
            fallback = {"score": 50, "reasoning": "Content filter triggered — fallback score. Manual review recommended."}
            return {CATEGORY_KEY_MAP[k]: fallback for k in ["clarity", "application", "engagement"]}
        raise

    from schema import CATEGORY_KEY_MAP, validate_llm_response
    raw = validate_llm_response(resp.choices[0].message.content, {
        "clarity": ["score", "reasoning"],
        "application": ["score", "reasoning"],
        "engagement": ["score", "reasoning"],
    })

    result = {}
    for snake_key in ["clarity", "application", "engagement"]:
        camel_key = CATEGORY_KEY_MAP[snake_key]
        result[camel_key] = {"score": raw[snake_key]["score"], "reasoning": raw[snake_key]["reasoning"]}
    return result


def pass3_delivery(input_data):
    """Pass 3: Delivery via GPT-5-nano."""
    client = _openai_client()
    transcript = input_data["transcript"]
    audio = input_data["audioMetrics"]
    wpm = input_data["wpm"]
    has_audio = input_data.get("audioAvailable", True)

    if has_audio:
        system_msg = """You are a sermon delivery analyst. You receive a transcript and pre-computed audio metrics. Use BOTH to score.

Audio metric guide: Pitch std >40Hz=expressive, <20Hz=monotone. Pitch range >300Hz=very dynamic. Intensity range >60dB=strong volume variation. Pauses >15/min=deliberate, <5/min=rushed. WPM 120-150=deliberate, 150-170=conversational, >170=fast.

SCORING SCALE — use the FULL 0-100 range:
  0-15:  Unlistenable — constant filler, monotone, no vocal control
  15-30: Poor — excessive filler words, flat delivery, no intentional pacing
  30-50: Below average — some expression but lacks confidence or vocal variety
  50-65: Average — competent but unremarkable; some vocal variety, occasional filler, adequate pacing
  65-75: Above average — generally confident with some dynamic moments but inconsistent
  75-85: Good — confident, expressive, intentional pacing
  85-95: Excellent — commanding presence, masterful vocal dynamics
  95-100: Exceptional — Spurgeon/MLK-tier oratory

CALIBRATION — MID-RANGE (most sermons):
  Delivery 50-60: Adequate pacing, occasional filler words, pitch variation exists but is not purposeful
  Delivery 60-70: Generally confident, some intentional pauses, but vocal dynamics are inconsistent
  Emotional Range 45-60: Speaker has some tonal variation but stays mostly in one register (e.g., always upbeat or always serious)
  Emotional Range 60-70: Noticeable shifts between 2 registers but lacks the full spectrum of gravity/joy/urgency/tenderness

CALIBRATION — EXTREMES:
- A casual, conversational tone with frequent filler words and no rhetorical craft = Delivery 25-40
- TTS/robotic audio with no natural inflection = Delivery 15-30
- Emotional Range measures PURPOSEFUL tonal variation in service of the sermon's message — not just "the speaker has energy"
- A speaker who is uniformly casual/jokey with no gravity, urgency, tenderness, or conviction = Emotional Range 20-35
- Emotional Range requires CONTRAST: moving between gravity and joy, urgency and tenderness, conviction and compassion
- A monotone or single-register delivery (even if energetic) = Emotional Range 15-30

METHODOLOGY: First describe what you observe in the audio metrics and transcript, THEN derive scores."""
        audio_section = f"""AUDIO METRICS:
- Pitch: {audio['pitchMeanHz']}Hz mean, {audio['pitchStdHz']}Hz std, {audio['pitchRangeHz']}Hz range
- Volume: {audio['intensityMeanDb']}dB mean, {audio['intensityRangeDb']}dB range
- Pauses: {audio['pauseCount']} total ({audio['pausesPerMinute']}/min)
- WPM: {wpm}
- Duration: {audio['durationSeconds']}s"""
        confidence_note = ""
    else:
        system_msg = """You are a sermon delivery analyst. Audio analysis was unavailable for this sermon — score based on transcript text cues ONLY (sentence structure, rhetorical devices, pacing indicators, punctuation patterns). Set confidence_level to "low" since audio data is missing. Score conservatively in the 50-75 range unless transcript strongly indicates otherwise.

SCORING SCALE — use the FULL 0-100 range, not just 40-90:
  0-15:  Unlistenable — constant filler, no rhetorical craft evident in text
  15-30: Poor — excessive filler words, no intentional pacing or structure
  30-50: Below average — some expression but lacks confidence or variety
  50-70: Average — competent delivery cues with room for improvement
  70-85: Good — confident, varied sentence structure, rhetorical devices
  85-95: Excellent — commanding prose, masterful rhetorical craft
  95-100: Exceptional — Spurgeon/MLK-tier oratory evident even in text"""
        audio_section = f"AUDIO METRICS: Not available (audio analysis failed)\n- WPM: {wpm}"
        confidence_note = "\nIMPORTANT: Note in reasoning that scores are text-only estimates without audio data."

    from openai import BadRequestError
    try:
        resp = client.chat.completions.create(
            model="gpt-5-nano",
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": system_msg},
                {"role": "user", "content": f"""{audio_section}

TRANSCRIPT:
{transcript}

Return JSON:
- "delivery": {{"score": 0-100, "filler_words": {{}}, "filler_total": int, "fillers_per_minute": float, "wpm": {wpm}, "pacing_assessment": "...", "confidence_level": "high/moderate/low", "reasoning": "..."}}
- "emotional_range": {{"score": 0-100, "tone_shifts": int, "passion_moments": [descriptions], "sentiment_arc": "...", "reasoning": "..."}}{confidence_note}"""},
            ],
        )
    except BadRequestError as e:
        if "content_filter" in str(e) or "content management policy" in str(e):
            log.warning("[pass3_delivery] Content filter triggered, returning fallback scores")
            from schema import CATEGORY_KEY_MAP
            return {
                CATEGORY_KEY_MAP["delivery"]: {"score": 50, "reasoning": "Content filter triggered — fallback score. Manual review recommended."},
                CATEGORY_KEY_MAP["emotional_range"]: {"score": 50, "reasoning": "Content filter triggered — fallback score. Manual review recommended."},
            }
        raise

    from schema import CATEGORY_KEY_MAP, validate_llm_response
    raw = validate_llm_response(resp.choices[0].message.content, {
        "delivery": ["score", "reasoning"],
        "emotional_range": ["score", "reasoning"],
    })

    result = {}
    for snake_key in ["delivery", "emotional_range"]:
        camel_key = CATEGORY_KEY_MAP[snake_key]
        result[camel_key] = {"score": raw[snake_key]["score"], "reasoning": raw[snake_key]["reasoning"]}
    return result


def pass4_enrichment(input_data):
    """Pass 4: Detect biblical language references and church history mentions."""
    client = _openai_client()
    transcript = input_data["transcript"]

    resp = client.chat.completions.create(
        model="gpt-5-nano",
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": """You analyze sermon transcripts for biblical language usage, church history references, and illustration types. Return JSON only."""},
            {"role": "user", "content": f"""Analyze this sermon transcript for three things:

1. **Biblical language references** — Any time the speaker references, translates, or explains a word from Hebrew, Greek, or Aramaic. Include:
   - Explicit mentions ("the Greek word agape means...")
   - Transliterated terms used without naming the language (e.g. "hesed", "logos", "shalom", "ruach")
   - Translation discussions ("this word is better translated as...")
   - Root word analysis
   Do NOT count English Bible quotations — only actual foreign language references.
   Do NOT count fully naturalized English words (amen, hallelujah, sabbath, messiah, angel, apostle, baptize, paradise) — only terms the speaker is actively translating or explaining.

2. **Church history references** — Post-biblical CHRISTIAN/THEOLOGICAL history only. Include:
   - Church fathers and theologians (Augustine, Luther, Calvin, Spurgeon, Wesley, Aquinas, etc.)
   - Church events/movements (Reformation, Great Awakening, Council of Nicaea, etc.)
   - Creeds/confessions (Nicene Creed, Westminster Confession, etc.)
   - Era references ("the early church fathers", "16th century reformers")
   - Modern Christian leaders/pastors referenced by name (Billy Graham, Bonhoeffer, etc.)
   Do NOT count biblical figures (Paul, Peter, Moses) — only post-biblical history.
   Do NOT count secular political figures (presidents, politicians, generals), secular events (wars, elections, court cases), pop culture, or general world history unless the reference is specifically about their role in CHURCH history.

3. **Illustrations** — Classify each illustration, anecdote, or example the speaker uses. Categories:
   - "personalStory": Speaker shares from their own life
   - "historical": References to historical events, figures, or eras (non-biblical, non-church-history)
   - "hypothetical": Thought experiments, "imagine if...", "what if..." scenarios
   - "humor": Jokes, funny stories, comedic moments
   Only count ACTUAL illustrations — not passing mentions.

Return JSON:
{{
  "biblicalLanguages": {{"count": <number>, "references": [{{"quote": "<short excerpt>", "language": "Hebrew|Greek|Aramaic", "term": "<the foreign term>"}}]}},
  "churchHistory": {{"count": <number>, "references": [{{"quote": "<short excerpt>", "figure_or_event": "<name>", "era": "<era or century>"}}]}},
  "illustrations": {{"total": <number>, "byType": {{"personalStory": [{{"quote": "<short excerpt>", "context": "<1-sentence summary>"}}], "historical": [...], "hypothetical": [...], "humor": [...]}}}}
}}

TRANSCRIPT:
{transcript}"""},
        ],
    )
    from schema import validate_flat_response
    raw = validate_flat_response(resp.choices[0].message.content, {
        "biblicalLanguages": {"count": 0, "references": []},
        "churchHistory": {"count": 0, "references": []},
        "illustrations": {"total": 0, "byType": {"personalStory": [], "historical": [], "hypothetical": [], "humor": []}},
    })

    bl = raw.get("biblicalLanguages", {})
    ch = raw.get("churchHistory", {})
    bl["count"] = len(bl.get("references", []))
    ch["count"] = len(ch.get("references", []))

    ill = raw.get("illustrations", {})
    by_type = ill.get("byType", {})
    ill["total"] = sum(len(by_type.get(k, [])) for k in ("personalStory", "historical", "hypothetical", "humor"))
    ill["byType"] = by_type

    return {"enrichment": {"biblicalLanguages": bl, "churchHistory": ch, "illustrations": ill}}


def classify_sermon(input_data):
    """Classify sermon type + extract metadata via GPT-5-nano."""
    client = _openai_client()
    transcript = input_data["transcript"]

    words = transcript.split()
    n = len(words)
    third = n // 3
    first = " ".join(words[:min(250, third)])
    middle = " ".join(words[max(0, n // 2 - 125):n // 2 + 125])
    last = " ".join(words[max(0, n - 250):])

    resp = client.chat.completions.create(
        model="gpt-5-nano",
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": "Classify the sermon and extract metadata. Return JSON only."},
            {"role": "user", "content": f"""Classify as: expository, topical, or survey.
- Expository: deep dive into a single passage, verse-by-verse. Even if the intro has anecdotes or background, if the core walks through a specific passage, it's expository.
- Topical: organized around a theme, drawing from multiple unrelated passages
- Survey: overview of a large section of scripture

IMPORTANT: Don't judge only by the intro. Look at MIDDLE and END sections.

Also extract:
- "title": sermon title (infer from content if not stated)
- "pastor": speaker name (if mentioned, else null)
- "main_passage": primary scripture passage (e.g. "Romans 8:28-30", else null)

Return: {{"sermon_type": "expository|topical|survey", "confidence": 0-100, "title": "...", "pastor": null or "...", "main_passage": null or "...", "reasoning": "one sentence"}}

TRANSCRIPT — BEGINNING:
{first}

TRANSCRIPT — MIDDLE:
{middle}

TRANSCRIPT — END:
{last}"""},
        ],
    )
    from schema import validate_flat_response
    raw = validate_flat_response(resp.choices[0].message.content, {
        "sermon_type": "topical", "confidence": 50, "title": "Untitled", "pastor": None, "main_passage": None,
    })

    return {
        "sermonType": raw.get("sermon_type", "topical"),
        "confidence": raw.get("confidence", 50),
        "title": input_data.get("userTitle") or raw.get("title", "Untitled"),
        "pastor": input_data.get("userPastor") or raw.get("pastor"),
        "mainPassage": raw.get("main_passage"),
    }


def classify_segments(input_data):
    """Label transcript segments by type for frontend color-coding."""
    client = _openai_client()
    segments = input_data["segments"]
    valid_types = {"scripture", "teaching", "application", "anecdote", "illustration", "prayer", "transition"}
    BATCH_SIZE = 200

    all_types = []
    for batch_start in range(0, len(segments), BATCH_SIZE):
        batch = segments[batch_start:batch_start + BATCH_SIZE]
        seg_lines = [f"[{i}] {seg['text'][:200]}" for i, seg in enumerate(batch)]

        resp = client.chat.completions.create(
            model="gpt-5-nano",
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": """Classify each sermon transcript segment into exactly one type:
- "scripture": direct Bible reading or quotation
- "teaching": exposition, explanation, theology
- "application": practical takeaways, calls to action
- "anecdote": personal stories, illustrations
- "illustration": historical examples, analogies
- "prayer": prayer
- "transition": transitions, greetings, housekeeping

Return JSON: {"types": [type_string_for_each_segment_in_order]}"""},
                {"role": "user", "content": "\n".join(seg_lines)},
            ],
        )
        from schema import validate_flat_response
        raw = validate_flat_response(resp.choices[0].message.content, {"types": []})
        batch_types = raw.get("types", [])
        while len(batch_types) < len(batch):
            batch_types.append("teaching")
        all_types.extend(batch_types[:len(batch)])

    result = []
    for i, seg in enumerate(segments):
        seg_type = all_types[i] if i < len(all_types) and all_types[i] in valid_types else "teaching"
        result.append({"start": seg["start"], "end": seg["end"], "text": seg["text"], "type": seg_type})
    return result


def generate_summary(input_data):
    """Generate summary + strengths + improvements from scores."""
    client = _openai_client()
    from schema import build_summary_prompt

    prompt = build_summary_prompt(input_data["categories"], input_data["sermonType"])
    resp = client.chat.completions.create(
        model="gpt-5-nano",
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": "You summarize sermon evaluation results. Return JSON only."},
            {"role": "user", "content": prompt},
        ],
    )
    from schema import validate_flat_response
    return validate_flat_response(resp.choices[0].message.content, {"summary": "", "strengths": [], "improvements": []})
