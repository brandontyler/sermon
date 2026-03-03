"""Activity functions for the sermon processing pipeline.

Each function is a Durable Functions activity that does one thing.
The orchestrator (function_app.py) coordinates them.
"""

import logging
import os
import tempfile

import numpy as np
from openai import AzureOpenAI

log = logging.getLogger(__name__)

# ─────────────────────────────────────────────
#  Shared
# ─────────────────────────────────────────────

def _openai_client():
    return AzureOpenAI(
        api_key=os.environ["OPENAI_KEY"],
        api_version=os.environ["OPENAI_API_VERSION"],
        azure_endpoint=os.environ["OPENAI_ENDPOINT"],
        max_retries=3,
        timeout=300,
    )


def _cosmos_client():
    from azure.cosmos import CosmosClient
    client = CosmosClient.from_connection_string(os.environ["COSMOS_CONNECTION_STRING"])
    return client.get_database_client("psr").get_container_client("sermons")


def _blob_client(blob_url):
    from azure.storage.blob import BlobClient
    return BlobClient.from_connection_string(os.environ["STORAGE_CONNECTION_STRING"], "sermon-audio", blob_url)


# ─────────────────────────────────────────────
#  Transcription (Azure AI Speech fast API)
# ─────────────────────────────────────────────

def transcribe(input_data):
    """Transcribe audio via Azure AI Speech fast transcription API.

    Input: {"blobUrl": str, "sermonId": str}
    Output: {"fullText": str, "wordCount": int, "durationMs": int, "wpm": float, "segments": [...]}

    Matches POC #6 (azure_fast_transcription_poc.py) SDK usage.
    """
    from azure.storage.blob import BlobClient
    from azure.core.credentials import AzureKeyCredential
    from azure.ai.transcription import TranscriptionClient
    from azure.ai.transcription.models import TranscriptionContent, TranscriptionOptions

    blob = BlobClient.from_connection_string(
        os.environ["STORAGE_CONNECTION_STRING"], "sermon-audio", input_data["blobUrl"]
    )
    audio_bytes = blob.download_blob().readall()

    client = TranscriptionClient(
        endpoint=os.environ["SPEECH_ENDPOINT"],
        credential=AzureKeyCredential(os.environ["SPEECH_KEY"]),
    )

    ext = os.path.splitext(input_data["blobUrl"])[1] or ".mp3"
    with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as f:
        f.write(audio_bytes)
        tmp_path = f.name

    try:
        with open(tmp_path, "rb") as audio_file:
            options = TranscriptionOptions(locales=["en-US"])
            content = TranscriptionContent(definition=options, audio=audio_file)
            result = client.transcribe(content)
    finally:
        os.unlink(tmp_path)

    full_text = result.combined_phrases[0].text if result.combined_phrases else ""
    duration_ms = result.duration_milliseconds or 0
    word_count = len(full_text.split())
    wpm = round(word_count / (duration_ms / 60000), 1) if duration_ms > 0 else 0

    # Build segments from phrases with timestamps
    segments = []
    if result.phrases:
        for phrase in result.phrases:
            offset_ms = phrase.offset_milliseconds or 0
            dur_ms = phrase.duration_milliseconds or 0
            segments.append({
                "start": round(offset_ms / 1000, 2),
                "end": round((offset_ms + dur_ms) / 1000, 2),
                "text": phrase.text,
                "type": "teaching",  # default; segment classification overrides later
            })

    return {
        "fullText": full_text,
        "wordCount": word_count,
        "durationMs": int(duration_ms),
        "wpm": wpm,
        "segments": segments,
    }


# ─────────────────────────────────────────────
#  Parselmouth Audio Analysis
# ─────────────────────────────────────────────

def analyze_audio(input_data):
    """Extract pitch, intensity, pause metrics via Parselmouth.

    Input: {"blobUrl": str}
    Output: audio metrics dict
    """
    import parselmouth

    blob = _blob_client(input_data["blobUrl"])
    audio_bytes = blob.download_blob().readall()

    ext = os.path.splitext(input_data["blobUrl"])[1] or ".mp3"
    with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as f:
        f.write(audio_bytes)
        tmp_path = f.name

    try:
        snd = parselmouth.Sound(tmp_path)
    finally:
        os.unlink(tmp_path)

    pitch = snd.to_pitch(time_step=0.1)
    intensity = snd.to_intensity(time_step=0.1)

    pv = pitch.selected_array["frequency"]
    voiced = pv[pv > 0]
    iv = intensity.values[0]

    # POC #8 fix: filter intensity noise floor (5th percentile)
    noise_floor = float(np.percentile(iv, 5))
    iv_filtered = iv[iv > noise_floor]

    # Pause detection
    threshold = float(np.percentile(iv, 20))
    transitions = np.diff((iv < threshold).astype(int))
    pause_count = int(np.sum(transitions == 1))

    return {
        "pitchMeanHz": round(float(np.mean(voiced)), 1) if len(voiced) > 0 else 0,
        "pitchStdHz": round(float(np.std(voiced)), 1) if len(voiced) > 0 else 0,
        "pitchRangeHz": round(float(np.max(voiced) - np.min(voiced)), 1) if len(voiced) > 0 else 0,
        "intensityMeanDb": round(float(np.mean(iv_filtered)), 1) if len(iv_filtered) > 0 else 0,
        "intensityRangeDb": round(float(np.max(iv_filtered) - np.min(iv_filtered)), 1) if len(iv_filtered) > 0 else 0,
        "noiseFloorDb": round(noise_floor, 1),
        "pauseCount": pause_count,
        "pausesPerMinute": round(pause_count / (snd.duration / 60), 1) if snd.duration > 0 else 0,
        "durationSeconds": round(snd.duration, 1),
    }


# ─────────────────────────────────────────────
#  LLM Scoring Passes (proven prompts from POC #7/#10)
# ─────────────────────────────────────────────

def pass1_biblical(input_data):
    """Pass 1: Biblical Analysis via o4-mini.

    Input: {"transcript": str}
    Output: {"biblicalAccuracy": {...}, "timeInTheWord": {...}, "passageFocus": {...}}
    """
    client = _openai_client()
    transcript = input_data["transcript"]

    resp = client.chat.completions.create(
        model="o4-mini",
        response_format={"type": "json_object"},
        messages=[{"role": "user", "content": f"""You are a biblical scholarship engine analyzing a sermon transcript. Return JSON with:

- "biblical_accuracy": {{"score": 0-100, "scripture_refs_found": [list of "Book Chapter:Verse" references detected], "refs_used_in_context": count, "refs_out_of_context": count, "reasoning": "..."}}
- "time_in_the_word": {{"score": 0-100, "biblical_content_pct": estimated %, "direct_quotation_pct": estimated %, "anecdote_pct": estimated %, "reasoning": "..."}}
  IMPORTANT: "Time in the Word" measures BIBLICAL CONTENT DENSITY — not just direct quotation. Score based on how much is grounded in biblical truth (quoted, taught, applied, exposited) vs secular content. 90-100=nearly all biblical, 70-89=majority, 50-69=mix, 30-49=more illustration, 0-29=minimal.
- "passage_focus": {{"score": 0-100, "main_passage": "...", "time_on_main_passage_pct": %, "tangent_count": int, "reasoning": "..."}}

Be rigorous. Check whether each scripture reference is used in its proper context.

SERMON TRANSCRIPT:
{transcript}"""}],
    )
    from schema import CATEGORY_KEY_MAP, validate_llm_response
    raw = validate_llm_response(resp.choices[0].message.content, {
        "biblical_accuracy": ["score", "reasoning"],
        "time_in_the_word": ["score", "reasoning"],
        "passage_focus": ["score", "reasoning"],
    })

    result = {}
    for snake_key in ["biblical_accuracy", "time_in_the_word", "passage_focus"]:
        camel_key = CATEGORY_KEY_MAP[snake_key]
        result[camel_key] = {
            "score": raw[snake_key]["score"],
            "reasoning": raw[snake_key]["reasoning"],
        }
    return result


def pass2_structure(input_data):
    """Pass 2: Structure & Content via GPT-4.1.

    Input: {"transcript": str}
    Output: {"clarity": {...}, "application": {...}, "engagement": {...}}
    """
    client = _openai_client()
    transcript = input_data["transcript"]

    resp = client.chat.completions.create(
        model="gpt-41",
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": """You are a sermon structure analyst. Evaluate against these rubrics and return JSON.

CLARITY (10%): Logical flow, clear transitions, identifiable structure, accessible language.
APPLICATION (10%): Practical takeaways, "so what?" moments, imperative language, specificity.
ENGAGEMENT (10%): Rhetorical variety, audience connection, illustration quality, content pacing."""},
            {"role": "user", "content": f"""Evaluate this sermon transcript:

{transcript}

Return JSON:
- "clarity": {{"score": 0-100, "structure_points": [main points], "transition_quality": "strong/moderate/weak", "reasoning": "..."}}
- "application": {{"score": 0-100, "actionable_takeaways": [list], "application_moments": count, "reasoning": "..."}}
- "engagement": {{"score": 0-100, "rhetorical_devices": [list], "audience_connection": "strong/moderate/weak", "reasoning": "..."}}"""},
        ],
    )
    from schema import CATEGORY_KEY_MAP, validate_llm_response
    raw = validate_llm_response(resp.choices[0].message.content, {
        "clarity": ["score", "reasoning"],
        "application": ["score", "reasoning"],
        "engagement": ["score", "reasoning"],
    })

    result = {}
    for snake_key in ["clarity", "application", "engagement"]:
        camel_key = CATEGORY_KEY_MAP[snake_key]
        result[camel_key] = {
            "score": raw[snake_key]["score"],
            "reasoning": raw[snake_key]["reasoning"],
        }
    return result


def pass3_delivery(input_data):
    """Pass 3: Delivery via GPT-4.1-mini.

    Input: {"transcript": str, "audioMetrics": dict, "wpm": float}
    Output: {"delivery": {...}, "emotionalRange": {...}}
    """
    client = _openai_client()
    transcript = input_data["transcript"]
    audio = input_data["audioMetrics"]
    wpm = input_data["wpm"]

    resp = client.chat.completions.create(
        model="gpt-41-mini",
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": """You are a sermon delivery analyst. You receive a transcript and pre-computed audio metrics. Use BOTH to score.

Audio metric guide: Pitch std >40Hz=expressive, <20Hz=monotone. Pitch range >300Hz=very dynamic. Intensity range >60dB=strong volume variation. Pauses >15/min=deliberate, <5/min=rushed. WPM 120-150=deliberate, 150-170=conversational, >170=fast."""},
            {"role": "user", "content": f"""AUDIO METRICS:
- Pitch: {audio['pitchMeanHz']}Hz mean, {audio['pitchStdHz']}Hz std, {audio['pitchRangeHz']}Hz range
- Volume: {audio['intensityMeanDb']}dB mean, {audio['intensityRangeDb']}dB range
- Pauses: {audio['pauseCount']} total ({audio['pausesPerMinute']}/min)
- WPM: {wpm}
- Duration: {audio['durationSeconds']}s

TRANSCRIPT:
{transcript}

Return JSON:
- "delivery": {{"score": 0-100, "filler_words": {{}}, "filler_total": int, "fillers_per_minute": float, "wpm": {wpm}, "pacing_assessment": "...", "confidence_level": "high/moderate/low", "reasoning": "..."}}
- "emotional_range": {{"score": 0-100, "tone_shifts": int, "passion_moments": [descriptions], "sentiment_arc": "...", "reasoning": "..."}}"""},
        ],
    )
    from schema import CATEGORY_KEY_MAP, validate_llm_response
    raw = validate_llm_response(resp.choices[0].message.content, {
        "delivery": ["score", "reasoning"],
        "emotional_range": ["score", "reasoning"],
    })

    result = {}
    for snake_key in ["delivery", "emotional_range"]:
        camel_key = CATEGORY_KEY_MAP[snake_key]
        result[camel_key] = {
            "score": raw[snake_key]["score"],
            "reasoning": raw[snake_key]["reasoning"],
        }
    return result


# ─────────────────────────────────────────────
#  Classification + Metadata (POC #8 fix: sample begin+mid+end)
# ─────────────────────────────────────────────

def classify_sermon(input_data):
    """Classify sermon type + extract metadata via GPT-4.1-mini.

    Input: {"transcript": str, "userTitle": str|None, "userPastor": str|None}
    Output: {"sermonType": str, "confidence": int, "title": str, "pastor": str|None, "mainPassage": str|None}
    """
    client = _openai_client()
    transcript = input_data["transcript"]

    # POC #8 fix: sample beginning + middle + end
    words = transcript.split()
    n = len(words)
    third = n // 3
    first = " ".join(words[:min(250, third)])
    middle = " ".join(words[max(0, n // 2 - 125):n // 2 + 125])
    last = " ".join(words[max(0, n - 250):])

    resp = client.chat.completions.create(
        model="gpt-41-mini",
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
        "sermon_type": "topical",
        "confidence": 50,
        "title": "Untitled",
        "pastor": None,
        "main_passage": None,
    })

    # User-provided values take priority
    return {
        "sermonType": raw.get("sermon_type", "topical"),
        "confidence": raw.get("confidence", 50),
        "title": input_data.get("userTitle") or raw.get("title", "Untitled"),
        "pastor": input_data.get("userPastor") or raw.get("pastor"),
        "mainPassage": raw.get("main_passage"),
    }


# ─────────────────────────────────────────────
#  Segment Classification (sermon-3lu — new, not POC'd)
# ─────────────────────────────────────────────

def classify_segments(input_data):
    """Label transcript segments by type for frontend color-coding.

    Input: {"segments": [{"start": float, "end": float, "text": str}]}
    Output: [{"start": float, "end": float, "text": str, "type": str}]

    Batches at 200 segments to maintain classification accuracy on long sermons.
    """
    client = _openai_client()
    segments = input_data["segments"]
    valid_types = {"scripture", "teaching", "application", "anecdote", "illustration", "prayer", "transition"}
    BATCH_SIZE = 200

    all_types = []
    for batch_start in range(0, len(segments), BATCH_SIZE):
        batch = segments[batch_start:batch_start + BATCH_SIZE]
        seg_lines = [f"[{i}] {seg['text'][:200]}" for i, seg in enumerate(batch)]

        resp = client.chat.completions.create(
            model="gpt-41-mini",
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
        # Pad if model returned fewer than expected
        while len(batch_types) < len(batch):
            batch_types.append("teaching")
        all_types.extend(batch_types[:len(batch)])

    result = []
    for i, seg in enumerate(segments):
        seg_type = all_types[i] if i < len(all_types) and all_types[i] in valid_types else "teaching"
        result.append({
            "start": seg["start"],
            "end": seg["end"],
            "text": seg["text"],
            "type": seg_type,
        })
    return result


# ─────────────────────────────────────────────
#  Summary Generation
# ─────────────────────────────────────────────

def generate_summary(input_data):
    """Generate summary + strengths + improvements from scores.

    Input: {"categories": dict, "sermonType": str}
    Output: {"summary": str, "strengths": [str], "improvements": [str]}
    """
    client = _openai_client()
    from schema import build_summary_prompt

    prompt = build_summary_prompt(input_data["categories"], input_data["sermonType"])
    resp = client.chat.completions.create(
        model="gpt-41-mini",
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": "You summarize sermon evaluation results. Return JSON only."},
            {"role": "user", "content": prompt},
        ],
    )
    from schema import validate_flat_response
    return validate_flat_response(resp.choices[0].message.content, {
        "summary": "",
        "strengths": [],
        "improvements": [],
    })


# ─────────────────────────────────────────────
#  Cosmos DB Update
# ─────────────────────────────────────────────

def update_sermon(input_data):
    """Patch a sermon document in Cosmos DB.

    Input: {"sermonId": str, "updates": dict}
    """
    container = _cosmos_client()
    sermon_id = input_data["sermonId"]
    updates = input_data["updates"]

    try:
        doc = container.read_item(sermon_id, partition_key=sermon_id)
    except Exception as e:
        if "NotFound" in type(e).__name__ or "CosmosResourceNotFoundError" in type(e).__name__:
            log.error(f"Sermon {sermon_id} not found in Cosmos — cannot update")
            return {"ok": False, "error": "not_found"}
        raise

    doc.update(updates)
    container.upsert_item(doc)
    return {"ok": True}
