#!/usr/bin/env python3
"""
PSR POC #10 — Scoring Calibration: "Time in the Word" Redefined

Tests the impact of redefining "Time in the Word" from direct scripture quotation %
to biblical content density (theology, doctrine, biblical concepts — not just quotes).

Runs Pass 1 only (o4-mini) on all 5 scored sermons with the new prompt, then compares
against POC #7-9 baselines.

Usage:
    source .venv/bin/activate
    python poc/calibration_time_in_word.py
"""

import json
import subprocess
import time
from pathlib import Path

REGION = "eastus2"
RG = "rg-sermon-rating-dev"
OPENAI_RESOURCE = "psr-openai-dev"

WEIGHTS = {
    "biblical_accuracy": 0.25, "time_in_the_word": 0.20, "passage_focus": 0.10,
    "clarity": 0.10, "engagement": 0.10, "application": 0.10,
    "delivery": 0.10, "emotional_range": 0.05,
}

# --- The updated Pass 1 prompt ---
PASS1_PROMPT = """You are a biblical scholarship engine analyzing a sermon transcript. Return JSON with:

- "biblical_accuracy": {{"score": 0-100, "scripture_refs_found": [list], "refs_used_in_context": count, "refs_out_of_context": count, "reasoning": "..."}}

- "time_in_the_word": {{"score": 0-100, "biblical_content_pct": estimated %, "direct_quotation_pct": estimated %, "anecdote_pct": estimated %, "reasoning": "..."}}
  IMPORTANT: "Time in the Word" measures BIBLICAL CONTENT DENSITY — not just direct scripture quotation. A preacher who weaves biblical theology, doctrine, and scriptural concepts throughout their sermon scores HIGH even if they don't read long passages aloud. Score based on how much of the sermon is grounded in biblical truth (quoted, taught, applied, or exposited), vs secular content (personal stories, cultural references, humor unrelated to scripture).
  - 90-100: Nearly every point is rooted in scripture or biblical theology
  - 70-89: Majority of content is biblically grounded with some illustrations
  - 50-69: Mix of biblical and non-biblical content
  - 30-49: More illustration/anecdote than biblical substance
  - 0-29: Minimal biblical content

- "passage_focus": {{"score": 0-100, "main_passage": "...", "time_on_main_passage_pct": %, "tangent_count": int, "reasoning": "..."}}

Be rigorous. Check whether each scripture reference is used in its proper context.

SERMON TRANSCRIPT:
{transcript}"""


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
                print(f"    ⚠ Rate limited, waiting {wait}s...")
                time.sleep(wait)
            else:
                raise


def run_pass1(client, text):
    return json.loads(call_with_backoff(lambda: client.chat.completions.create(
        model="o4-mini", response_format={"type": "json_object"},
        messages=[{"role": "user", "content": PASS1_PROMPT.format(transcript=text)}]
    ).choices[0].message.content))


# Sermons to test — all 5 we've scored
SERMONS = [
    {
        "name": "Spurgeon: Compel Them to Come In",
        "file": "poc/samples/spurgeon_compel_them_to_come_in.txt",
        "old_tw": 60, "old_composite": 85.9,
        "old_scores": {"biblical_accuracy": 98, "time_in_the_word": 60, "passage_focus": 50,
                       "clarity": 88, "engagement": 98, "application": 94, "delivery": 85, "emotional_range": 95},
    },
    {
        "name": "Spurgeon: Immutability of God",
        "file": "poc/samples/spurgeon_immutability_of_god.txt",
        "old_tw": 30, "old_composite": 72.8,
        "old_scores": {"biblical_accuracy": 90, "time_in_the_word": 30, "passage_focus": 85,
                       "clarity": 85, "engagement": 90, "application": 65, "delivery": 75, "emotional_range": 85},
    },
    {
        "name": "Spurgeon: Power of the Holy Spirit",
        "file": "poc/samples/spurgeon_power_of_the_holy_spirit.txt",
        "old_tw": 70, "old_composite": 80.7,
        "old_scores": {"biblical_accuracy": 88, "time_in_the_word": 70, "passage_focus": 30,
                       "clarity": 88, "engagement": 91, "application": 82, "delivery": 75, "emotional_range": 85},
    },
    {
        "name": "Piper: Romans 8:28-30",
        "file": "poc/fast_transcription_result_piper_called_according_to_his_purpose.json",
        "is_json": True,
        "old_tw": 75, "old_composite": 83.9,
        "old_scores": {"biblical_accuracy": 90, "time_in_the_word": 75, "passage_focus": 85,
                       "clarity": 85, "engagement": 92, "application": 72, "delivery": 85, "emotional_range": 90},
    },
    {
        "name": "Scheer: 1 Peter 1:1-2",
        "file": "poc/fast_transcription_result_scheer_elect_exiles_1peter1v1_20260208.json",
        "is_json": True,
        "old_tw": 65, "old_composite": 84.7,
        "old_scores": {"biblical_accuracy": 90, "time_in_the_word": 65, "passage_focus": 70,
                       "clarity": 75, "engagement": 70, "application": 65, "delivery": 85, "emotional_range": 88},
    },
]


def main():
    print("=" * 65)
    print("  PSR POC #10 — Calibration: Time in the Word Redefined")
    print("  Old: % of sermon spent quoting scripture")
    print("  New: Biblical content density (theology + doctrine + quotes)")
    print("=" * 65)

    key = get_key()
    client = make_client(key)
    results = []

    for i, s in enumerate(SERMONS):
        if i > 0:
            print(f"\n  ⏳ Waiting 60s for TPM reset...")
            time.sleep(60)

        # Load text
        if s.get("is_json"):
            ft = json.loads(Path(s["file"]).read_text())
            text = ft["full_text"]
        else:
            text = Path(s["file"]).read_text()

        print(f"\n  [{i+1}/{len(SERMONS)}] {s['name']} ({len(text.split())} words)")

        t0 = time.time()
        p1 = run_pass1(client, text)
        elapsed = round(time.time() - t0, 1)
        print(f"    ✓ Pass 1 complete ({elapsed}s)")

        new_tw = p1["time_in_the_word"]["score"]
        new_ba = p1["biblical_accuracy"]["score"]
        new_pf = p1["passage_focus"]["score"]

        # Recompute composite with new Pass 1 scores, keeping old Pass 2/3 scores
        new_scores = dict(s["old_scores"])
        new_scores["biblical_accuracy"] = new_ba
        new_scores["time_in_the_word"] = new_tw
        new_scores["passage_focus"] = new_pf
        new_composite = round(sum(new_scores[k] * WEIGHTS[k] for k in WEIGHTS), 1)

        delta_tw = new_tw - s["old_tw"]
        delta_comp = round(new_composite - s["old_composite"], 1)

        results.append({
            "name": s["name"],
            "old_tw": s["old_tw"], "new_tw": new_tw, "delta_tw": delta_tw,
            "old_ba": s["old_scores"]["biblical_accuracy"], "new_ba": new_ba,
            "old_pf": s["old_scores"]["passage_focus"], "new_pf": new_pf,
            "old_composite": s["old_composite"], "new_composite": new_composite,
            "delta_composite": delta_comp,
            "pass1_detail": p1,
        })

        print(f"    Time in Word: {s['old_tw']} → {new_tw} (Δ {delta_tw:+d})")
        print(f"    Biblical Acc: {s['old_scores']['biblical_accuracy']} → {new_ba}")
        print(f"    Passage Focus: {s['old_scores']['passage_focus']} → {new_pf}")
        print(f"    Composite: {s['old_composite']} → {new_composite} (Δ {delta_comp:+.1f})")

    # Save results
    output = {
        "pipeline": "psr-poc10-calibration-time-in-word",
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "change": "Redefined 'Time in the Word' from direct scripture quotation % to biblical content density",
        "results": results,
    }
    out_path = Path("poc/calibration_time_in_word_results.json")
    out_path.write_text(json.dumps(output, indent=2))

    # Summary table
    print(f"\n{'=' * 65}")
    print(f"  CALIBRATION RESULTS — Time in the Word Redefined")
    print(f"{'=' * 65}")
    print(f"\n  {'Sermon':<35} {'Old TW':>6} {'New TW':>6} {'Δ TW':>5} {'Old PSR':>7} {'New PSR':>7} {'Δ PSR':>6}")
    print(f"  {'-' * 73}")
    for r in results:
        print(f"  {r['name']:<35} {r['old_tw']:>6} {r['new_tw']:>6} {r['delta_tw']:>+5} {r['old_composite']:>7} {r['new_composite']:>7} {r['delta_composite']:>+6.1f}")

    print(f"\n  Results: {out_path}")
    print("=" * 65)


if __name__ == "__main__":
    main()
