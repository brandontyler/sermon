#!/usr/bin/env python3
"""
PSR POC #9 — Spurgeon Historical Benchmark (Text-Only Scoring)

Scores Spurgeon sermon transcripts through the 3-pass multi-model pipeline.
No audio = no Parselmouth, so Delivery and Emotional Range use text-only signals.
Throttle-aware: estimates tokens per pass, sequences across sermons with 60s gaps.

Usage:
    source .venv/bin/activate
    python poc/spurgeon_scoring.py
"""

import json
import subprocess
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

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

DEPLOYMENT_LIMITS = {
    "o4-mini": {"tpm": 80_000}, "gpt-41": {"tpm": 50_000}, "gpt-41-mini": {"tpm": 80_000},
}

SERMONS = [
    {
        "file": "poc/samples/spurgeon_compel_them_to_come_in.txt",
        "title": "Compel Them to Come In",
        "number": 227, "passage": "Luke 14:23", "date": "December 5, 1858",
        "note": "Spurgeon's self-proclaimed greatest sermon — most conversions",
    },
    {
        "file": "poc/samples/spurgeon_immutability_of_god.txt",
        "title": "The Immutability of God",
        "number": 1, "passage": "Malachi 3:6", "date": "1855",
        "note": "Spurgeon's very first published sermon",
    },
    {
        "file": "poc/samples/spurgeon_power_of_the_holy_spirit.txt",
        "title": "The Power of the Holy Spirit",
        "number": 30, "passage": "Romans 15:13", "date": "1855",
        "note": "Top-ranked doctrinal sermon on the Holy Spirit",
    },
]


def get_key():
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
        max_retries=0, timeout=300)


def call_with_backoff(fn, initial_wait=60, max_retries=3):
    for attempt in range(max_retries + 1):
        try:
            return fn()
        except Exception as e:
            if "429" in str(e) and attempt < max_retries:
                wait = initial_wait * (2 ** attempt)
                print(f"    ⚠ Rate limited, waiting {wait}s (attempt {attempt + 1}/{max_retries})...")
                time.sleep(wait)
            else:
                raise


def estimate_tokens(word_count):
    """Estimate total tokens for all 4 passes combined per deployment."""
    per_pass = int(word_count * 1.3) + 500 + 800
    o4_extra = 800 * 5  # reasoning tokens
    return {
        "o4-mini": per_pass + o4_extra,  # 1 pass (biblical)
        "gpt-41": per_pass,              # 1 pass (structure)
        "gpt-41-mini": per_pass * 2,     # 2 passes (delivery + classify)
    }


def pass1_biblical(client, text):
    return json.loads(call_with_backoff(lambda: client.chat.completions.create(
        model=MODELS["biblical"], response_format={"type": "json_object"},
        messages=[{"role": "user", "content": f"""You are a biblical scholarship engine analyzing a sermon transcript. Return JSON with:

- "biblical_accuracy": {{"score": 0-100, "scripture_refs_found": [list], "refs_used_in_context": count, "refs_out_of_context": count, "reasoning": "..."}}
- "time_in_the_word": {{"score": 0-100, "scripture_percentage": estimated %, "anecdote_percentage": estimated %, "reasoning": "..."}}
- "passage_focus": {{"score": 0-100, "main_passage": "...", "time_on_main_passage_pct": %, "tangent_count": int, "reasoning": "..."}}

Be rigorous. Check whether each scripture reference is used in its proper context.

SERMON TRANSCRIPT:
{text}"""}]).choices[0].message.content))


def pass2_structure(client, text):
    return json.loads(call_with_backoff(lambda: client.chat.completions.create(
        model=MODELS["structure"], response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": """You are a sermon structure analyst. Return JSON.
CLARITY (10%): Logical flow, clear transitions, identifiable structure, accessible language.
APPLICATION (10%): Practical takeaways, "so what?" moments, imperative language, specificity.
ENGAGEMENT (10%): Rhetorical variety, audience connection, illustration quality, content pacing."""},
            {"role": "user", "content": f"""Evaluate this sermon transcript:

{text}

Return JSON:
- "clarity": {{"score": 0-100, "structure_points": [main points], "transition_quality": "strong/moderate/weak", "reasoning": "..."}}
- "application": {{"score": 0-100, "actionable_takeaways": [list], "application_moments": count, "reasoning": "..."}}
- "engagement": {{"score": 0-100, "rhetorical_devices": [list], "audience_connection": "strong/moderate/weak", "reasoning": "..."}}"""}]
    ).choices[0].message.content))


def pass3_delivery(client, text):
    """Text-only delivery scoring — no Parselmouth data available for historical sermons."""
    return json.loads(call_with_backoff(lambda: client.chat.completions.create(
        model=MODELS["delivery"], response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": """You are a sermon delivery analyst. This is a WRITTEN TRANSCRIPT of a historical sermon (no audio available). Score delivery and emotional range based on TEXT SIGNALS ONLY:
- Sentence variety (length, structure)
- Exclamatory language, rhetorical questions
- Repetition for emphasis
- Vocabulary richness
- Emotional language and tone shifts
- Dramatic pacing in the text

Note: filler words and vocal metrics are unavailable. Score conservatively on delivery (text cannot fully capture vocal performance) but score emotional range normally since written rhetoric reveals emotional arc."""},
            {"role": "user", "content": f"""TRANSCRIPT (text only, no audio):
{text}

Return JSON:
- "delivery": {{"score": 0-100, "filler_words": {{}}, "filler_total": 0, "wpm": "N/A (text only)", "pacing_assessment": "...", "confidence_level": "text-only estimate", "reasoning": "..."}}
- "emotional_range": {{"score": 0-100, "tone_shifts": int, "passion_moments": [descriptions], "sentiment_arc": "...", "reasoning": "..."}}"""}]
    ).choices[0].message.content))


def classify_sermon(client, text):
    words = text.split()
    n = len(words)
    first = " ".join(words[:min(250, n // 3)])
    middle = " ".join(words[max(0, n // 2 - 125):n // 2 + 125])
    last = " ".join(words[max(0, n - 250):])
    return json.loads(call_with_backoff(lambda: client.chat.completions.create(
        model=MODELS["classify"], response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": "Classify the sermon type. Return JSON only."},
            {"role": "user", "content": f"""Classify as: expository, topical, or survey.
- Expository: deep dive into a single passage, verse-by-verse.
- Topical: organized around a theme, drawing from multiple unrelated passages
- Survey: overview of a large section of scripture

IMPORTANT: Don't judge only by the intro. Look at MIDDLE and END sections.

Return: {{"sermon_type": "expository|topical|survey", "confidence": 0-100, "reasoning": "one sentence"}}

BEGINNING:
{first}

MIDDLE:
{middle}

END:
{last}"""}]
    ).choices[0].message.content))


def score_sermon(client, sermon_info, text):
    """Score a single sermon — all 4 passes in parallel (throttle-safe for ~7K words)."""
    word_count = len(text.split())
    est = estimate_tokens(word_count)
    safe = all(est[m] < int(DEPLOYMENT_LIMITS[m]["tpm"] * 0.8) for m in est)

    print(f"\n  Token estimates: {', '.join(f'{m}={t:,}' for m, t in est.items())}")
    print(f"  All fit within 80% TPM: {'YES — running parallel' if safe else 'NO — sequencing'}")

    pass_fns = {
        "pass1_biblical": lambda: pass1_biblical(client, text),
        "pass2_structure": lambda: pass2_structure(client, text),
        "pass3_delivery": lambda: pass3_delivery(client, text),
        "classify": lambda: classify_sermon(client, text),
    }

    results = {}
    timings = {}

    if safe:
        # All parallel
        def timed(name):
            t0 = time.time()
            r = pass_fns[name]()
            timings[name] = round(time.time() - t0, 1)
            return name, r

        with ThreadPoolExecutor(max_workers=4) as pool:
            futures = [pool.submit(timed, n) for n in pass_fns]
            for f in as_completed(futures):
                name, data = f.result()
                results[name] = data
                print(f"    ✓ {name} ({timings[name]}s)")
    else:
        # Sequential with gaps
        for name, fn in pass_fns.items():
            t0 = time.time()
            results[name] = fn()
            timings[name] = round(time.time() - t0, 1)
            print(f"    ✓ {name} ({timings[name]}s)")
            time.sleep(30)

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

    return {
        "sermon_info": sermon_info,
        "word_count": word_count,
        "models_used": MODELS,
        "timings_seconds": timings,
        "sermon_classification": classification,
        "pass1_biblical": p1,
        "pass2_structure": p2,
        "pass3_delivery": p3,
        "raw_scores": raw,
        "normalized_scores": norm,
        "composite_psr": composite,
        "scoring_note": "Text-only scoring — no audio metrics available for historical sermons. "
                        "Delivery score is text-based estimate (conservative). "
                        "Emotional Range scored from written rhetoric.",
    }


def main():
    print("=" * 60)
    print("  PSR POC #9 — Spurgeon Historical Benchmark")
    print("  Text-Only Scoring (no audio available)")
    print("=" * 60)

    key = get_key()
    client = make_client(key)
    all_results = []

    for i, sermon in enumerate(SERMONS):
        text = Path(sermon["file"]).read_text()
        word_count = len(text.split())

        print(f"\n{'─' * 60}")
        print(f"  [{i+1}/{len(SERMONS)}] {sermon['title']}")
        print(f"  {sermon['passage']} | Sermon #{sermon['number']} | {sermon['date']}")
        print(f"  {sermon['note']}")
        print(f"  Words: {word_count}")

        if i > 0:
            # Wait 60s between sermons for TPM window reset
            print(f"\n  ⏳ Waiting 60s for TPM window reset between sermons...")
            time.sleep(60)

        result = score_sermon(client, sermon, text)
        all_results.append(result)

        # Print scorecard
        ns = result["normalized_scores"]
        raw = result["raw_scores"]
        st = result["sermon_classification"].get("sermon_type", "?")
        conf = result["sermon_classification"].get("confidence", "?")
        print(f"\n  COMPOSITE PSR: {result['composite_psr']}/100 | Type: {st} ({conf}%)")
        print(f"  {'Category':<22} {'Raw':>5} {'Norm':>5}")
        print(f"  {'-' * 34}")
        for cat in WEIGHTS:
            label = cat.replace("_", " ").title()
            print(f"  {label:<22} {raw[cat]:>5} {ns[cat]:>5}")

    # Save all results
    output = {
        "pipeline": "psr-poc9-spurgeon-historical-benchmark",
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "scoring_mode": "text-only (no audio)",
        "sermons": all_results,
    }
    out_path = Path("poc/spurgeon_benchmark_results.json")
    out_path.write_text(json.dumps(output, indent=2))

    # Print comparison table
    print(f"\n{'=' * 60}")
    print(f"  SPURGEON BENCHMARK — COMPARISON")
    print(f"{'=' * 60}")
    print(f"\n  {'Sermon':<30} {'Composite':>9} {'Type':<12} {'Words':>6}")
    print(f"  {'-' * 60}")
    for r in all_results:
        title = r["sermon_info"]["title"][:28]
        print(f"  {title:<30} {r['composite_psr']:>7}/100 {r['sermon_classification'].get('sermon_type', '?'):<12} {r['word_count']:>6}")

    # Cross-preacher comparison
    print(f"\n  --- vs Modern Preachers ---")
    print(f"  {'Preacher':<25} {'Sermon':<25} {'Composite':>9}")
    print(f"  {'-' * 60}")
    for r in all_results:
        print(f"  {'Spurgeon':<25} {r['sermon_info']['title'][:23]:<25} {r['composite_psr']:>7}/100")
    print(f"  {'Piper':<25} {'Romans 8:28-30':<25} {'83.9':>7}/100")
    print(f"  {'Scheer':<25} {'1 Peter 1:1-2':<25} {'84.7':>7}/100")

    print(f"\n  Full results: {out_path}")
    print("=" * 60)


if __name__ == "__main__":
    main()
