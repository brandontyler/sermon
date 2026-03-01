#!/usr/bin/env python3
"""
PSR POC #5 — Azure Multi-Model Pipeline

Full production-mirror pipeline using Azure services:
  - Azure AI Speech: transcription with timestamps + diarization
  - Parselmouth: audio metrics (pitch, intensity, pauses)
  - o4-mini: Pass 1 — Biblical Analysis (Accuracy, Time in Word, Passage Focus)
  - GPT-4.1: Pass 2 — Structure & Content (Clarity, Application, Engagement)
  - GPT-4.1-mini: Pass 3 — Delivery (Delivery, Emotional Range) + sermon type classification

Usage:
    source .venv/bin/activate
    python poc/azure_multipass_poc.py poc/samples/piper_called_according_to_his_purpose.mp3
    python poc/azure_multipass_poc.py poc/samples/piper_called_according_to_his_purpose.mp3 --skip-transcribe
"""

import argparse
import json
import os
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import numpy as np

# --- Config ---

REGION = "eastus2"
RG = "rg-sermon-rating-dev"
OPENAI_RESOURCE = "psr-openai-dev"
SPEECH_RESOURCE = "psr-speech-dev"

# Deployment names (as created in Azure)
MODELS = {
    "biblical": "o4-mini",       # Pass 1: reasoning for scripture verification
    "structure": "gpt-41",       # Pass 2: instruction-following for rubric eval
    "delivery": "gpt-41-mini",   # Pass 3: interpret pre-computed audio data
    "classify": "gpt-41-mini",   # Classification (nano unavailable, mini is fine)
}


def get_azure_keys():
    """Fetch keys from Azure CLI (no hardcoded secrets)."""
    def az_key(resource):
        r = subprocess.run(
            ["az", "cognitiveservices", "account", "keys", "list",
             "--name", resource, "--resource-group", RG, "--query", "key1", "-o", "tsv"],
            capture_output=True, text=True
        )
        return r.stdout.strip()

    return {
        "openai_key": az_key(OPENAI_RESOURCE),
        "speech_key": az_key(SPEECH_RESOURCE),
        "openai_endpoint": f"https://{REGION}.api.cognitive.microsoft.com/",
    }


# --- Step 1: Azure AI Speech Transcription ---

def ensure_wav(audio_path: str) -> str:
    """Convert to 16kHz mono WAV if needed (Azure Speech SDK requirement)."""
    if audio_path.endswith(".wav"):
        return audio_path
    wav_path = audio_path.rsplit(".", 1)[0] + ".wav"
    if not Path(wav_path).exists():
        print(f"  Converting to WAV for Azure Speech SDK...")
        subprocess.run(
            ["ffmpeg", "-i", audio_path, "-ar", "16000", "-ac", "1", "-y", wav_path],
            capture_output=True, check=True,
        )
    return wav_path


def transcribe_azure(audio_path: str, speech_key: str, cache_path: Path) -> dict:
    """Transcribe via Azure AI Speech — chunks audio for reliability on long files."""
    if cache_path.exists():
        print("  Using cached Azure transcript")
        return json.loads(cache_path.read_text())

    import azure.cognitiveservices.speech as speechsdk

    wav_path = ensure_wav(audio_path)

    # Get duration
    import parselmouth
    total_duration = parselmouth.Sound(audio_path).duration

    # Split into ~5 min chunks to avoid session timeout
    chunk_seconds = 300
    chunk_count = int(np.ceil(total_duration / chunk_seconds))
    print(f"  Transcribing via Azure AI Speech: {wav_path}")
    print(f"  Duration: {total_duration:.0f}s — splitting into {chunk_count} chunks")

    chunk_dir = Path(wav_path).parent / "chunks"
    chunk_dir.mkdir(exist_ok=True)

    all_text = []
    for i in range(chunk_count):
        start = i * chunk_seconds
        chunk_path = chunk_dir / f"chunk_{i:03d}.wav"
        if not chunk_path.exists():
            subprocess.run(
                ["ffmpeg", "-i", wav_path, "-ss", str(start), "-t", str(chunk_seconds),
                 "-ar", "16000", "-ac", "1", "-y", str(chunk_path)],
                capture_output=True, check=True,
            )

        config = speechsdk.SpeechConfig(subscription=speech_key, region=REGION)
        audio_config = speechsdk.audio.AudioConfig(filename=str(chunk_path))
        recognizer = speechsdk.SpeechRecognizer(speech_config=config, audio_config=audio_config)

        chunk_text = []
        done = False

        def on_recognized(evt):
            if evt.result.reason == speechsdk.ResultReason.RecognizedSpeech:
                chunk_text.append(evt.result.text)

        def on_stopped(evt):
            nonlocal done
            done = True

        recognizer.recognized.connect(on_recognized)
        recognizer.session_stopped.connect(on_stopped)
        recognizer.canceled.connect(on_stopped)

        recognizer.start_continuous_recognition()
        timeout = time.time() + 180
        while not done and time.time() < timeout:
            time.sleep(0.5)
        recognizer.stop_continuous_recognition()

        all_text.extend(chunk_text)
        print(f"    Chunk {i+1}/{chunk_count}: {len(chunk_text)} segments")

    full_text = " ".join(all_text)
    result = {"text": full_text, "duration": round(total_duration, 1)}
    cache_path.write_text(json.dumps(result, indent=2))
    print(f"  ✓ {len(full_text.split())} words, {total_duration:.0f}s")

    # Cleanup chunks
    import shutil
    shutil.rmtree(chunk_dir, ignore_errors=True)

    return result


# --- Step 2: Parselmouth Audio Analysis ---

def analyze_audio(audio_path: str) -> dict:
    """Extract pitch, intensity, pause metrics."""
    import parselmouth

    snd = parselmouth.Sound(audio_path)
    pitch = snd.to_pitch(time_step=0.1)
    intensity = snd.to_intensity(time_step=0.1)

    pv = pitch.selected_array["frequency"]
    voiced = pv[pv > 0]
    iv = intensity.values[0]

    threshold = np.percentile(iv, 20)
    transitions = np.diff((iv < threshold).astype(int))
    pause_count = int(np.sum(transitions == 1))
    duration_min = snd.duration / 60

    return {
        "pitch_mean_hz": round(float(np.mean(voiced)), 1) if len(voiced) else 0,
        "pitch_std_hz": round(float(np.std(voiced)), 1) if len(voiced) else 0,
        "pitch_range_hz": round(float(np.max(voiced) - np.min(voiced)), 1) if len(voiced) else 0,
        "intensity_mean_db": round(float(np.mean(iv)), 1),
        "intensity_range_db": round(float(np.max(iv) - np.min(iv)), 1),
        "pause_count": pause_count,
        "pauses_per_minute": round(pause_count / duration_min, 1),
        "duration_seconds": round(snd.duration, 1),
    }


# --- Step 3: Multi-Model LLM Passes ---

def make_client(keys):
    """Create Azure OpenAI client."""
    from openai import AzureOpenAI
    return AzureOpenAI(
        api_key=keys["openai_key"],
        api_version="2025-01-01-preview",
        azure_endpoint=keys["openai_endpoint"],
    )


def pass1_biblical(client, transcript: str) -> dict:
    """o4-mini: Biblical Accuracy, Time in the Word, Passage Focus."""
    resp = client.chat.completions.create(
        model=MODELS["biblical"],
        response_format={"type": "json_object"},
        messages=[{
            "role": "user",
            "content": f"""You are a biblical scholarship engine analyzing a sermon transcript. Return JSON with:

- "biblical_accuracy": {{
    "score": 0-100,
    "scripture_refs_found": [list of "Book Chapter:Verse" references detected],
    "refs_used_in_context": count of references used correctly in context,
    "refs_out_of_context": count of references used out of context or misquoted,
    "reasoning": brief explanation of score
  }}
- "time_in_the_word": {{
    "score": 0-100,
    "scripture_percentage": estimated % of sermon spent in scripture/biblical content,
    "anecdote_percentage": estimated % spent on personal stories/illustrations,
    "reasoning": brief explanation
  }}
- "passage_focus": {{
    "score": 0-100,
    "main_passage": the primary passage being preached,
    "time_on_main_passage_pct": estimated % of sermon on the main passage,
    "tangent_count": number of significant departures from main passage,
    "reasoning": brief explanation
  }}

Be rigorous. Check whether each scripture reference is used in its proper context — does the preacher represent what the text actually says? Score based on textual fidelity, not theological tradition.

SERMON TRANSCRIPT:
{transcript}"""
        }],
    )
    return json.loads(resp.choices[0].message.content)


def pass2_structure(client, transcript: str) -> dict:
    """GPT-4.1: Clarity, Application, Engagement."""
    resp = client.chat.completions.create(
        model=MODELS["structure"],
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": """You are a sermon structure analyst. Evaluate the transcript against these rubrics and return JSON.

For each category, provide a score (0-100) and reasoning.

CLARITY (10% of PSR):
- Logical flow between points
- Clear transitions
- Identifiable structure (intro, points, conclusion)
- Accessible language for a general audience

APPLICATION (10% of PSR):
- Practical takeaways listeners can act on
- "So what?" moments — connecting scripture to daily life
- Imperative/action language ("Go and do...", "This week, try...")
- Specificity of application (vague "be better" vs concrete steps)

ENGAGEMENT (10% of PSR):
- Rhetorical variety (questions, repetition, callbacks)
- Audience connection cues ("you", "we", direct address)
- Illustration quality and relevance
- Pacing variation in content (not just vocal — does the content rhythm shift?)"""},
            {"role": "user", "content": f"""Evaluate this sermon transcript:

{transcript}

Return JSON:
- "clarity": {{"score": 0-100, "structure_points": [identified main points], "transition_quality": "strong/moderate/weak", "reasoning": "..."}}
- "application": {{"score": 0-100, "actionable_takeaways": [list], "application_moments": count, "reasoning": "..."}}
- "engagement": {{"score": 0-100, "rhetorical_devices": [list of techniques used], "audience_connection": "strong/moderate/weak", "reasoning": "..."}}"""}
        ],
    )
    return json.loads(resp.choices[0].message.content)


def pass3_delivery(client, transcript: str, audio_metrics: dict) -> dict:
    """GPT-4.1-mini: Delivery, Emotional Range (uses Parselmouth data)."""
    word_count = len(transcript.split())
    wpm = round(word_count / (audio_metrics["duration_seconds"] / 60), 1)

    resp = client.chat.completions.create(
        model=MODELS["delivery"],
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": """You are a sermon delivery analyst. You receive both a transcript and pre-computed audio metrics from Parselmouth analysis. Use BOTH to score delivery.

Audio metric interpretation guide:
- Pitch std > 40Hz = expressive, < 20Hz = monotone
- Pitch range > 300Hz = very dynamic vocal range
- Intensity range > 60dB = strong volume variation (whisper to emphasis)
- Pauses > 15/min = deliberate pacer (can be strength), < 5/min = rushed
- WPM 120-150 = deliberate, 150-170 = conversational, > 170 = fast"""},
            {"role": "user", "content": f"""AUDIO METRICS:
- Pitch: {audio_metrics['pitch_mean_hz']}Hz mean, {audio_metrics['pitch_std_hz']}Hz std, {audio_metrics['pitch_range_hz']}Hz range
- Volume: {audio_metrics['intensity_mean_db']}dB mean, {audio_metrics['intensity_range_db']}dB range
- Pauses: {audio_metrics['pause_count']} total ({audio_metrics['pauses_per_minute']}/min)
- WPM: {wpm}
- Duration: {audio_metrics['duration_seconds']}s

TRANSCRIPT:
{transcript}

Return JSON:
- "delivery": {{"score": 0-100, "filler_words": {{"word": count}}, "filler_total": int, "fillers_per_minute": float, "wpm": {wpm}, "pacing_assessment": "...", "confidence_level": "high/moderate/low", "reasoning": "..."}}
- "emotional_range": {{"score": 0-100, "tone_shifts": count of significant tone changes detected, "passion_moments": [brief descriptions], "sentiment_arc": "description of emotional journey", "reasoning": "..."}}"""}
        ],
    )
    return json.loads(resp.choices[0].message.content)


def classify_sermon(client, transcript: str) -> dict:
    """GPT-4.1-mini: Sermon type classification."""
    resp = client.chat.completions.create(
        model=MODELS["classify"],
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": "Classify the sermon type. Return JSON only."},
            {"role": "user", "content": f"""Classify this sermon as one of: expository, topical, or survey.

- Expository: deep dive into a single passage, verse-by-verse or section-by-section
- Topical: organized around a theme/topic, drawing from multiple passages
- Survey: overview of a large section of scripture (multiple chapters or a whole book)

Return: {{"sermon_type": "expository|topical|survey", "confidence": 0-100, "reasoning": "one sentence"}}

TRANSCRIPT (first 2000 chars):
{transcript[:2000]}"""}
        ],
    )
    return json.loads(resp.choices[0].message.content)


# --- Score Normalization (pure code, no LLM) ---

# Baseline adjustments by sermon type — topical sermons naturally have fewer
# scripture refs, so raw biblical scores get a boost. Expository sermons
# naturally score high on passage focus, so no adjustment needed there.
NORM_ADJUSTMENTS = {
    "expository": {"biblical_accuracy": 0, "time_in_the_word": 0, "passage_focus": 0},
    "topical":    {"biblical_accuracy": 5, "time_in_the_word": 8, "passage_focus": 10},
    "survey":     {"biblical_accuracy": 3, "time_in_the_word": 5, "passage_focus": 12},
}

WEIGHTS = {
    "biblical_accuracy": 0.25,
    "time_in_the_word": 0.20,
    "passage_focus": 0.10,
    "clarity": 0.10,
    "engagement": 0.10,
    "application": 0.10,
    "delivery": 0.10,
    "emotional_range": 0.05,
}


def normalize_and_composite(raw_scores: dict, sermon_type: str) -> dict:
    """Apply sermon-type normalization and compute weighted composite."""
    adj = NORM_ADJUSTMENTS.get(sermon_type, NORM_ADJUSTMENTS["topical"])
    normalized = {}
    for cat, score in raw_scores.items():
        bump = adj.get(cat, 0)
        normalized[cat] = min(100, score + bump)

    composite = sum(normalized[cat] * WEIGHTS[cat] for cat in WEIGHTS)
    return {"normalized_scores": normalized, "composite": round(composite, 1)}


# --- Main Pipeline ---

def run(audio_path: str, skip_transcribe: bool):
    print("=" * 60)
    print("  PSR POC #5 — Azure Multi-Model Pipeline")
    print("=" * 60)

    keys = get_azure_keys()
    poc_dir = Path(__file__).parent
    cache_path = poc_dir / f"azure_transcript_{Path(audio_path).stem}.json"

    # Step 1: Transcribe
    print("\n[Step 1] Azure AI Speech Transcription")
    transcript = transcribe_azure(audio_path, keys["speech_key"], cache_path)

    # Step 2: Audio analysis
    print("\n[Step 2] Parselmouth Audio Analysis")
    audio = analyze_audio(audio_path)
    print(f"  ✓ Pitch: {audio['pitch_mean_hz']}Hz ± {audio['pitch_std_hz']}Hz, range {audio['pitch_range_hz']}Hz")
    print(f"  ✓ Volume: {audio['intensity_range_db']}dB range")
    print(f"  ✓ Pauses: {audio['pause_count']} ({audio['pauses_per_minute']}/min)")

    # Step 3: Three parallel LLM passes + classification
    print("\n[Step 3] Multi-Model LLM Analysis (3 passes + classification)")
    client = make_client(keys)
    text = transcript["text"]

    results = {}
    timings = {}

    def timed_call(name, fn, *args):
        t0 = time.time()
        r = fn(*args)
        timings[name] = round(time.time() - t0, 1)
        return name, r

    with ThreadPoolExecutor(max_workers=4) as pool:
        futures = [
            pool.submit(timed_call, "pass1_biblical", pass1_biblical, client, text),
            pool.submit(timed_call, "pass2_structure", pass2_structure, client, text),
            pool.submit(timed_call, "pass3_delivery", pass3_delivery, client, text, audio),
            pool.submit(timed_call, "classify", classify_sermon, client, text),
        ]
        for f in as_completed(futures):
            name, data = f.result()
            results[name] = data
            print(f"  ✓ {name} complete ({timings[name]}s)")

    # Step 4: Assemble raw scores
    p1 = results["pass1_biblical"]
    p2 = results["pass2_structure"]
    p3 = results["pass3_delivery"]
    classification = results["classify"]

    raw_scores = {
        "biblical_accuracy": p1["biblical_accuracy"]["score"],
        "time_in_the_word": p1["time_in_the_word"]["score"],
        "passage_focus": p1["passage_focus"]["score"],
        "clarity": p2["clarity"]["score"],
        "application": p2["application"]["score"],
        "engagement": p2["engagement"]["score"],
        "delivery": p3["delivery"]["score"],
        "emotional_range": p3["emotional_range"]["score"],
    }

    # Step 5: Normalize + composite
    sermon_type = classification.get("sermon_type", "topical")
    print(f"\n[Step 4] Score Normalization (sermon type: {sermon_type})")
    final = normalize_and_composite(raw_scores, sermon_type)

    # Build full result
    result = {
        "pipeline": "psr-poc5-azure-multimodel",
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "source": audio_path,
        "models_used": MODELS,
        "timings_seconds": timings,
        "transcript_words": len(text.split()),
        "transcript_duration": transcript["duration"],
        "audio_metrics": audio,
        "sermon_classification": classification,
        "pass1_biblical": p1,
        "pass2_structure": p2,
        "pass3_delivery": p3,
        "raw_scores": raw_scores,
        "normalized_scores": final["normalized_scores"],
        "composite_psr": final["composite"],
    }

    out_path = poc_dir / f"multipass_result_{Path(audio_path).stem}.json"
    out_path.write_text(json.dumps(result, indent=2))

    # Print scorecard
    ns = final["normalized_scores"]
    print("\n" + "=" * 60)
    print(f"  PSR SCORECARD — {Path(audio_path).stem}")
    print(f"  Sermon Type: {sermon_type} ({classification.get('confidence', '?')}% confidence)")
    print("=" * 60)
    print(f"\n  COMPOSITE PSR: {final['composite']}/100")
    print(f"\n  {'Category':<22} {'Raw':>5} {'Norm':>5}  {'Weight':>6}")
    print(f"  {'-'*46}")
    for cat in WEIGHTS:
        label = cat.replace("_", " ").title()
        print(f"  {label:<22} {raw_scores[cat]:>5} {ns[cat]:>5}  {WEIGHTS[cat]*100:>5.0f}%")

    print(f"\n  --- Pass 1: Biblical (o4-mini, {timings.get('pass1_biblical', '?')}s) ---")
    ba = p1["biblical_accuracy"]
    print(f"  Scripture refs: {len(ba.get('scripture_refs_found', []))}")
    print(f"  In context: {ba.get('refs_used_in_context', '?')} | Out of context: {ba.get('refs_out_of_context', '?')}")
    print(f"  Main passage: {p1['passage_focus'].get('main_passage', '?')}")

    print(f"\n  --- Pass 2: Structure (GPT-4.1, {timings.get('pass2_structure', '?')}s) ---")
    cl = p2["clarity"]
    print(f"  Structure: {cl.get('transition_quality', '?')} transitions")
    if cl.get("structure_points"):
        for pt in cl["structure_points"][:4]:
            print(f"    • {pt}")
    ap = p2["application"]
    print(f"  Actionable takeaways: {ap.get('application_moments', '?')}")

    print(f"\n  --- Pass 3: Delivery (GPT-4.1-mini, {timings.get('pass3_delivery', '?')}s) ---")
    dl = p3["delivery"]
    print(f"  Fillers: {dl.get('filler_total', '?')} ({dl.get('fillers_per_minute', '?')}/min)")
    print(f"  WPM: {dl.get('wpm', '?')} | Confidence: {dl.get('confidence_level', '?')}")
    er = p3["emotional_range"]
    print(f"  Tone shifts: {er.get('tone_shifts', '?')} | Arc: {er.get('sentiment_arc', '?')}")

    print(f"\n  Full results: {out_path}")
    print("=" * 60)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="PSR POC #5 — Azure Multi-Model Pipeline")
    parser.add_argument("audio", help="Path to sermon audio file")
    parser.add_argument("--skip-transcribe", action="store_true", help="Reuse cached Azure transcript")
    args = parser.parse_args()
    run(args.audio, args.skip_transcribe)
