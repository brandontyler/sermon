#!/usr/bin/env python3
"""
PSR POC #7 — Validated Multipass Scoring on Full Transcript

POC #5 scored on a partial transcript (1,064 words / 28% of sermon).
POC #6 fixed transcription (3,762 words / 99.2% recovery).
This POC re-runs the 3-pass scoring on the FULL transcript to get validated scores.

Questions this POC answers:
  1. How do scores change with 3.5x more text?
  2. Does o4-mini find more scripture refs on the complete transcript?
  3. Is the 82.7 composite from POC #5 still in the right ballpark?

Usage:
    source .venv/bin/activate
    python poc/validated_multipass_poc.py poc/samples/piper_called_according_to_his_purpose.mp3

Cost: ~$0.09 (OpenAI only — reuses cached fast transcript + cached Parselmouth)
"""

import argparse
import json
import subprocess
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import numpy as np

REGION = "eastus2"
RG = "rg-sermon-rating-dev"
OPENAI_RESOURCE = "psr-openai-dev"

MODELS = {
    "biblical": "o4-mini",
    "structure": "gpt-41",
    "delivery": "gpt-41-mini",
    "classify": "gpt-41-mini",
}

WEIGHTS = {
    "biblical_accuracy": 0.25, "time_in_the_word": 0.20, "passage_focus": 0.10,
    "clarity": 0.10, "engagement": 0.10, "application": 0.10,
    "delivery": 0.10, "emotional_range": 0.05,
}

NORM_ADJUSTMENTS = {
    "expository": {"biblical_accuracy": 0, "time_in_the_word": 0, "passage_focus": 0},
    "topical":    {"biblical_accuracy": 5, "time_in_the_word": 8, "passage_focus": 10},
    "survey":     {"biblical_accuracy": 3, "time_in_the_word": 5, "passage_focus": 12},
}


def get_openai_key():
    r = subprocess.run(
        ["az", "cognitiveservices", "account", "keys", "list",
         "--name", OPENAI_RESOURCE, "--resource-group", RG, "--query", "key1", "-o", "tsv"],
        capture_output=True, text=True)
    return r.stdout.strip()


def make_client(key):
    from openai import AzureOpenAI
    return AzureOpenAI(
        api_key=key, api_version="2025-01-01-preview",
        azure_endpoint=f"https://{REGION}.api.cognitive.microsoft.com/",
        max_retries=3, timeout=300)


def call_with_backoff(fn, *args, initial_wait=60, max_retries=3):
    """Wrap an LLM call with exponential backoff for 429 rate limits."""
    for attempt in range(max_retries + 1):
        try:
            return fn(*args)
        except Exception as e:
            if "429" in str(e) and attempt < max_retries:
                wait = initial_wait * (2 ** attempt)
                print(f"    ⚠ Rate limited, waiting {wait}s (attempt {attempt + 1}/{max_retries})...")
                time.sleep(wait)
            else:
                raise


# --- Throttle-Aware Scheduler (shared with azure_multipass_poc.py) ---

DEPLOYMENT_LIMITS = {
    "o4-mini":     {"tpm": 80_000, "rpm": 80},
    "gpt-41":      {"tpm": 50_000, "rpm": 50},
    "gpt-41-mini": {"tpm": 80_000, "rpm": 80},
}
TOKEN_RATIO = 1.3
EST_OUTPUT_TOKENS = {"biblical": 800, "structure": 800, "delivery": 800, "classify": 200}
O4_MINI_REASONING_MULTIPLIER = 5


def estimate_tokens(pass_name, transcript_word_count):
    input_tokens = int(transcript_word_count * TOKEN_RATIO) + 500
    output_tokens = EST_OUTPUT_TOKENS.get(pass_name, 800)
    total = input_tokens + output_tokens
    if MODELS.get(pass_name) == "o4-mini":
        total += output_tokens * O4_MINI_REASONING_MULTIPLIER
    return total


def schedule_passes(transcript_word_count):
    passes = ["pass1_biblical", "pass2_structure", "pass3_delivery", "classify"]
    pass_to_model = {
        "pass1_biblical": MODELS["biblical"],
        "pass2_structure": MODELS["structure"],
        "pass3_delivery": MODELS["delivery"],
        "classify": MODELS["classify"],
    }
    pass_to_key = {
        "pass1_biblical": "biblical", "pass2_structure": "structure",
        "pass3_delivery": "delivery", "classify": "classify",
    }
    token_est = {p: estimate_tokens(pass_to_key[p], transcript_word_count) for p in passes}

    deployment_passes = {}
    for p in passes:
        deployment_passes.setdefault(pass_to_model[p], []).append(p)

    deployment_batches = {}
    for model, model_passes in deployment_passes.items():
        limit = int(DEPLOYMENT_LIMITS.get(model, {"tpm": 50_000})["tpm"] * 0.8)
        batches, current, current_tokens = [], [], 0
        for p in model_passes:
            if current_tokens + token_est[p] > limit and current:
                batches.append(current)
                current, current_tokens = [p], token_est[p]
            else:
                current.append(p)
                current_tokens += token_est[p]
        if current:
            batches.append(current)
        deployment_batches[model] = batches

    max_batches = max(len(b) for b in deployment_batches.values())
    execution_plan = []
    for i in range(max_batches):
        batch = []
        for batches in deployment_batches.values():
            if i < len(batches):
                batch.extend(batches[i])
        execution_plan.append(batch)
    return execution_plan, token_est


def pass1_biblical(client, transcript):
    resp = client.chat.completions.create(
        model=MODELS["biblical"], response_format={"type": "json_object"},
        messages=[{"role": "user", "content": f"""You are a biblical scholarship engine analyzing a sermon transcript. Return JSON with:

- "biblical_accuracy": {{"score": 0-100, "scripture_refs_found": [list of "Book Chapter:Verse" references detected], "refs_used_in_context": count, "refs_out_of_context": count, "reasoning": "..."}}
- "time_in_the_word": {{"score": 0-100, "biblical_content_pct": estimated %, "direct_quotation_pct": estimated %, "anecdote_pct": estimated %, "reasoning": "..."}}
  IMPORTANT: "Time in the Word" measures BIBLICAL CONTENT DENSITY — not just direct quotation. Score based on how much is grounded in biblical truth (quoted, taught, applied, exposited) vs secular content. 90-100=nearly all biblical, 70-89=majority, 50-69=mix, 30-49=more illustration, 0-29=minimal.
- "passage_focus": {{"score": 0-100, "main_passage": "...", "time_on_main_passage_pct": %, "tangent_count": int, "reasoning": "..."}}

Be rigorous. Check whether each scripture reference is used in its proper context.

SERMON TRANSCRIPT:
{transcript}"""}])
    return json.loads(resp.choices[0].message.content)


def pass2_structure(client, transcript):
    resp = client.chat.completions.create(
        model=MODELS["structure"], response_format={"type": "json_object"},
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
- "engagement": {{"score": 0-100, "rhetorical_devices": [list], "audience_connection": "strong/moderate/weak", "reasoning": "..."}}"""}])
    return json.loads(resp.choices[0].message.content)


def pass3_delivery(client, transcript, audio_metrics):
    wpm = round(len(transcript.split()) / (audio_metrics["duration_seconds"] / 60), 1)
    resp = client.chat.completions.create(
        model=MODELS["delivery"], response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": """You are a sermon delivery analyst. You receive a transcript and pre-computed audio metrics. Use BOTH to score.

Audio metric guide: Pitch std >40Hz=expressive, <20Hz=monotone. Pitch range >300Hz=very dynamic. Intensity range >60dB=strong volume variation. Pauses >15/min=deliberate, <5/min=rushed. WPM 120-150=deliberate, 150-170=conversational, >170=fast."""},
            {"role": "user", "content": f"""AUDIO METRICS:
- Pitch: {audio_metrics['pitch_mean_hz']}Hz mean, {audio_metrics['pitch_std_hz']}Hz std, {audio_metrics['pitch_range_hz']}Hz range
- Volume: {audio_metrics['intensity_mean_db']}dB mean, {audio_metrics['intensity_range_db']}dB range
- Pauses: {audio_metrics['pause_count']} total ({audio_metrics['pauses_per_minute']}/min)
- WPM: {wpm}
- Duration: {audio_metrics['duration_seconds']}s

TRANSCRIPT:
{transcript}

Return JSON:
- "delivery": {{"score": 0-100, "filler_words": {{}}, "filler_total": int, "fillers_per_minute": float, "wpm": {wpm}, "pacing_assessment": "...", "confidence_level": "high/moderate/low", "reasoning": "..."}}
- "emotional_range": {{"score": 0-100, "tone_shifts": int, "passion_moments": [descriptions], "sentiment_arc": "...", "reasoning": "..."}}"""}])
    return json.loads(resp.choices[0].message.content)


def classify_sermon(client, transcript):
    """POC #8 fix: sample beginning + middle + end instead of just first 3000 chars."""
    words = transcript.split()
    n = len(words)
    third = n // 3
    first = " ".join(words[:min(250, third)])
    middle = " ".join(words[max(0, n//2 - 125):n//2 + 125])
    last = " ".join(words[max(0, n - 250):])

    resp = client.chat.completions.create(
        model=MODELS["classify"], response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": "Classify the sermon type. Return JSON only."},
            {"role": "user", "content": f"""Classify as: expository, topical, or survey.
- Expository: deep dive into a single passage, verse-by-verse. Even if the intro has anecdotes or background, if the core walks through a specific passage, it's expository.
- Topical: organized around a theme, drawing from multiple unrelated passages
- Survey: overview of a large section of scripture

IMPORTANT: Don't judge only by the intro. Look at MIDDLE and END sections.

Return: {{"sermon_type": "expository|topical|survey", "confidence": 0-100, "reasoning": "one sentence"}}

TRANSCRIPT — BEGINNING:
{first}

TRANSCRIPT — MIDDLE:
{middle}

TRANSCRIPT — END:
{last}"""}])
    return json.loads(resp.choices[0].message.content)


def run(audio_path):
    print("=" * 60)
    print("  PSR POC #7 — Validated Multipass on Full Transcript")
    print("=" * 60)

    poc_dir = Path(__file__).parent
    stem = Path(audio_path).stem

    # Load POC #6 fast transcript (cached)
    ft_path = poc_dir / f"fast_transcription_result_{stem}.json"
    if not ft_path.exists():
        print(f"\n  ERROR: No cached fast transcript at {ft_path}")
        print(f"  Run POC #6 first: python poc/azure_fast_transcription_poc.py {audio_path}")
        return
    ft = json.loads(ft_path.read_text())
    text = ft["full_text"]
    duration = ft["duration_milliseconds"] / 1000
    print(f"\n  Using POC #6 fast transcript: {ft['word_count']} words, {ft['duration_minutes']:.1f} min")

    # Reuse Parselmouth audio metrics from POC #5 result (same audio file)
    poc5_path = poc_dir / f"multipass_result_{stem}.json"
    if poc5_path.exists():
        poc5 = json.loads(poc5_path.read_text())
        audio = poc5["audio_metrics"]
        print(f"  Using cached Parselmouth metrics from POC #5")
    else:
        # Compute fresh if no POC #5 cache
        import parselmouth
        snd = parselmouth.Sound(audio_path)
        pitch = snd.to_pitch(time_step=0.1)
        intensity = snd.to_intensity(time_step=0.1)
        pv = pitch.selected_array["frequency"]
        voiced = pv[pv > 0]
        iv = intensity.values[0]
        # POC #8 fix: filter intensity noise floor
        noise_floor = np.percentile(iv, 5)
        iv_filtered = iv[iv > noise_floor]
        threshold = np.percentile(iv, 20)
        transitions = np.diff((iv < threshold).astype(int))
        pause_count = int(np.sum(transitions == 1))
        audio = {
            "pitch_mean_hz": round(float(np.mean(voiced)), 1),
            "pitch_std_hz": round(float(np.std(voiced)), 1),
            "pitch_range_hz": round(float(np.max(voiced) - np.min(voiced)), 1),
            "intensity_mean_db": round(float(np.mean(iv_filtered)), 1),
            "intensity_range_db": round(float(np.max(iv_filtered) - np.min(iv_filtered)), 1),
            "intensity_noise_floor_db": round(float(noise_floor), 1),
            "pause_count": pause_count,
            "pauses_per_minute": round(pause_count / (snd.duration / 60), 1),
            "duration_seconds": round(snd.duration, 1),
        }

    # Run throttle-aware passes
    print(f"\n[Scoring] Throttle-aware scheduling on {len(text.split())} words...")
    key = get_openai_key()
    client = make_client(key)

    execution_plan, token_est = schedule_passes(len(text.split()))
    print(f"  Token estimates: {', '.join(f'{p}={t:,}' for p, t in token_est.items())}")
    print(f"  Execution plan: {len(execution_plan)} batch(es) — {[b for b in execution_plan]}")

    pass_fns = {
        "pass1_biblical": lambda: pass1_biblical(client, text),
        "pass2_structure": lambda: pass2_structure(client, text),
        "pass3_delivery": lambda: pass3_delivery(client, text, audio),
        "classify": lambda: classify_sermon(client, text),
    }

    results = {}
    timings = {}

    for batch_idx, batch in enumerate(execution_plan):
        if batch_idx > 0:
            print(f"  ⏳ Waiting 60s for TPM window reset before batch {batch_idx + 1}...")
            time.sleep(60)
        print(f"  Batch {batch_idx + 1}/{len(execution_plan)}: {batch}")

        def timed(name):
            t0 = time.time()
            r = call_with_backoff(pass_fns[name])
            timings[name] = round(time.time() - t0, 1)
            return name, r

        with ThreadPoolExecutor(max_workers=len(batch)) as pool:
            futures = [pool.submit(timed, name) for name in batch]
            for f in as_completed(futures):
                name, data = f.result()
                results[name] = data
                print(f"    ✓ {name} ({timings[name]}s)")

    p1, p2, p3 = results["pass1_biblical"], results["pass2_structure"], results["pass3_delivery"]
    classification = results["classify"]

    raw = {
        "biblical_accuracy": p1["biblical_accuracy"]["score"],
        "time_in_the_word": p1["time_in_the_word"]["score"],
        "passage_focus": p1["passage_focus"]["score"],
        "clarity": p2["clarity"]["score"],
        "application": p2["application"]["score"],
        "engagement": p2["engagement"]["score"],
        "delivery": p3["delivery"]["score"],
        "emotional_range": p3["emotional_range"]["score"],
    }

    sermon_type = classification.get("sermon_type", "topical")
    adj = NORM_ADJUSTMENTS.get(sermon_type, {})
    norm = {k: min(100, v + adj.get(k, 0)) for k, v in raw.items()}
    composite = round(sum(norm[k] * WEIGHTS[k] for k in WEIGHTS), 1)

    # Load POC #5 scores for comparison
    poc5_raw = poc5.get("raw_scores", {}) if poc5_path.exists() else {}

    # Build result
    result = {
        "pipeline": "psr-poc7-validated-multipass",
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "source": audio_path,
        "purpose": "Re-score POC #5 using POC #6's complete transcript (3,762 words vs 1,064)",
        "models_used": MODELS,
        "timings_seconds": timings,
        "transcript_source": "poc6_fast_transcription",
        "transcript_words": len(text.split()),
        "transcript_wpm": ft["wpm"],
        "audio_metrics": audio,
        "sermon_classification": classification,
        "pass1_biblical": p1,
        "pass2_structure": p2,
        "pass3_delivery": p3,
        "raw_scores": raw,
        "normalized_scores": norm,
        "composite_psr": composite,
        "comparison_vs_poc5": {
            "poc5_words": 1064,
            "poc7_words": len(text.split()),
            "poc5_composite": 82.7,
            "poc7_composite": composite,
            "delta": round(composite - 82.7, 1),
            "category_deltas": {k: raw[k] - poc5_raw.get(k, 0) for k in raw} if poc5_raw else {},
        },
    }

    out_path = poc_dir / f"validated_multipass_result_{stem}.json"
    out_path.write_text(json.dumps(result, indent=2))

    # Print scorecard with comparison
    print(f"\n{'=' * 60}")
    print(f"  PSR SCORECARD — VALIDATED (Full Transcript)")
    print(f"  Sermon Type: {sermon_type} ({classification.get('confidence', '?')}%)")
    print(f"  Words: {len(text.split())} (POC #5 had {1064})")
    print(f"{'=' * 60}")
    print(f"\n  COMPOSITE PSR: {composite}/100  (POC #5: 82.7 | Δ {composite - 82.7:+.1f})")
    print(f"\n  {'Category':<22} {'POC#7':>6} {'POC#5':>6} {'Δ':>5}  {'Weight':>6}")
    print(f"  {'-'*52}")
    for cat in WEIGHTS:
        label = cat.replace("_", " ").title()
        old = poc5_raw.get(cat, "—")
        delta = f"{raw[cat] - old:+d}" if isinstance(old, int) else "—"
        print(f"  {label:<22} {raw[cat]:>6} {old:>6} {delta:>5}  {WEIGHTS[cat]*100:>5.0f}%")

    ba = p1["biblical_accuracy"]
    print(f"\n  Scripture refs found: {len(ba.get('scripture_refs_found', []))} (POC #5: 6)")
    print(f"  In context: {ba.get('refs_used_in_context', '?')} | Out of context: {ba.get('refs_out_of_context', '?')}")

    dl = p3["delivery"]
    print(f"  WPM: {dl.get('wpm', '?')} (POC #5: 30.4)")
    print(f"  Fillers: {dl.get('filler_total', '?')}")

    print(f"\n  Results: {out_path}")
    print("=" * 60)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="PSR POC #7 — Validated Multipass on Full Transcript")
    parser.add_argument("audio", help="Path to sermon audio file")
    args = parser.parse_args()
    run(args.audio)
