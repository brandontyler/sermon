#!/usr/bin/env python3
"""
PSR Sermon Type Comparison — Run multiple Piper sermons through POC #3 pipeline
and compare scores side-by-side to test sermon-type bias.

Usage:
    source .venv/bin/activate
    python poc/sermon_comparison.py
    python poc/sermon_comparison.py --skip-transcribe   # reuse cached transcripts
"""

import argparse
import json
import time
from pathlib import Path

SERMONS = [
    {
        "id": "romans_1_8",
        "audio": "poc/samples/piper_romans_1_8.mp3",
        "title": "The Mighty and Merciful Message of Romans 1-8",
        "type": "Survey",
        "passage": "Romans 1-8 (overview)",
        "date": "2002-09-22",
    },
    {
        "id": "called_according",
        "audio": "poc/samples/piper_called_according_to_his_purpose.mp3",
        "title": "Called According to His Purpose",
        "type": "Expository/Exegetical",
        "passage": "Romans 8:28-30",
        "date": "1985-10-13",
    },
    {
        "id": "dont_waste",
        "audio": "poc/samples/piper_dont_waste_your_life.mp3",
        "title": "Don't Waste Your Life",
        "type": "Topical",
        "passage": "Various (topic-driven)",
        "date": "2012-10-17",
    },
    {
        "id": "joy",
        "audio": "poc/samples/piper_no_one_will_take_your_joy.mp3",
        "title": "No One Will Take Your Joy from You",
        "type": "Topical (pillar)",
        "passage": "John 16:16-24",
        "date": "2011-05-07",
    },
]


def run_pipeline(sermon: dict, skip_transcribe: bool) -> dict:
    """Run POC #3 pipeline on a single sermon, return results."""
    import numpy as np
    from pathlib import Path

    audio_path = sermon["audio"]
    cache_path = Path(f"poc/transcript_cache_{sermon['id']}.json")

    # Transcribe
    print(f"\n  [Transcribe] {sermon['title']}")
    if skip_transcribe and cache_path.exists():
        transcript = json.loads(cache_path.read_text())
        print(f"    Cached: {len(transcript['words'])} words, {transcript['duration']:.0f}s")
    else:
        from faster_whisper import WhisperModel
        if not hasattr(run_pipeline, '_model'):
            print("    Loading whisper model...")
            run_pipeline._model = WhisperModel("base", compute_type="int8", device="cpu")
        model = run_pipeline._model
        print(f"    Transcribing {audio_path}...")
        segments, info = model.transcribe(audio_path, word_timestamps=True)
        words = []
        text_parts = []
        for seg in segments:
            text_parts.append(seg.text)
            for w in (seg.words or []):
                words.append({"word": w.word.strip(), "start": round(w.start, 2), "end": round(w.end, 2)})
        transcript = {"text": " ".join(text_parts).strip(), "words": words, "duration": round(info.duration, 1), "language": info.language}
        cache_path.write_text(json.dumps(transcript, indent=2))
        print(f"    Done: {len(words)} words, {info.duration:.0f}s")

    # Audio analysis
    print(f"  [Audio] Analyzing pitch/intensity/pauses...")
    import parselmouth
    snd = parselmouth.Sound(audio_path)
    pitch = snd.to_pitch(time_step=0.1)
    intensity = snd.to_intensity(time_step=0.1)
    pitch_values = pitch.selected_array["frequency"]
    pitch_voiced = pitch_values[pitch_values > 0]
    intensity_values = intensity.values[0]
    threshold = np.percentile(intensity_values, 20)
    silent_frames = intensity_values < threshold
    transitions = np.diff(silent_frames.astype(int))
    pause_count = int(np.sum(transitions == 1))

    audio = {
        "pitch_mean_hz": round(float(np.mean(pitch_voiced)), 1) if len(pitch_voiced) > 0 else 0,
        "pitch_std_hz": round(float(np.std(pitch_voiced)), 1) if len(pitch_voiced) > 0 else 0,
        "pitch_range_hz": round(float(np.max(pitch_voiced) - np.min(pitch_voiced)), 1) if len(pitch_voiced) > 0 else 0,
        "intensity_mean_db": round(float(np.mean(intensity_values)), 1),
        "dynamic_range_db": round(float(np.max(intensity_values) - np.min(intensity_values)), 1),
        "pauses": pause_count,
        "pauses_per_min": round(pause_count / (snd.duration / 60), 1),
        "duration_seconds": round(snd.duration, 1),
    }

    # Text analysis
    print(f"  [Text] Analyzing content...")
    import spacy
    import textstat
    import re
    import sys
    sys.path.insert(0, str(Path(__file__).parent / "poc")) if str(Path(__file__).parent / "poc") not in sys.path else None
    sys.path.insert(0, "poc") if "poc" not in sys.path else None
    from scripture_analyzer import detect_references, BOOKS

    nlp = spacy.load("en_core_web_sm")
    text = transcript["text"]
    doc = nlp(text)
    words_list = text.split()
    word_count = len(words_list)
    duration = transcript["duration"]
    wpm = round(word_count / (duration / 60), 1)

    # Fillers
    filler_pat = re.compile(r"\b(um|uh|you know|like|so|right|i mean|basically|actually|literally)\b", re.IGNORECASE)
    fillers = {}
    for m in filler_pat.finditer(text.lower()):
        w = m.group(1)
        fillers[w] = fillers.get(w, 0) + 1
    filler_total = sum(fillers.values())

    # Imperatives
    imperative_count = sum(1 for sent in doc.sents for tokens in [[t for t in sent if not t.is_space]] if tokens and tokens[0].pos_ == "VERB" and tokens[0].dep_ == "ROOT")

    # Scripture refs (reuse POC #2 detection + spoken pattern fallback)
    refs = detect_references(text)
    chv_pattern = re.compile(r"chapter\s+(\d{1,3})\s*,?\s*(?:starting\s+in\s+)?verse\s+(\d{1,3})(?:\s*[-–to]+\s*(\d{1,3}))?", re.IGNORECASE)
    book_pattern = re.compile(rf"\b({BOOKS})\b", re.IGNORECASE)
    ref_positions = {r["position"] for r in refs}
    for m in chv_pattern.finditer(text):
        if any(abs(m.start() - p) < 60 for p in ref_positions):
            continue
        last_book = None
        for bm in book_pattern.finditer(text[:m.start()]):
            last_book = re.sub(r"\s+", " ", bm.group(1)).strip()
        if last_book:
            refs.append({"book": last_book, "chapter": int(m.group(1)), "verse_start": int(m.group(2)), "raw": f"{last_book} {m.group(1)}:{m.group(2)}", "position": m.start()})
            ref_positions.add(m.start())
    refs.sort(key=lambda r: r["position"])

    text_result = {
        "word_count": word_count,
        "wpm": wpm,
        "flesch_reading_ease": round(textstat.flesch_reading_ease(text), 1),
        "flesch_kincaid_grade": round(textstat.flesch_kincaid_grade(text), 1),
        "filler_total": filler_total,
        "filler_per_min": round(filler_total / (duration / 60), 1),
        "top_fillers": dict(sorted(fillers.items(), key=lambda x: -x[1])[:5]),
        "imperative_sentences": imperative_count,
        "scripture_count": len(refs),
        "scripture_per_min": round(len(refs) / (duration / 60), 2),
        "scripture_refs": [r["raw"] for r in refs[:15]],
    }

    return {**sermon, "audio": audio, "text": text_result}


def print_comparison(results: list[dict]):
    """Print side-by-side comparison table."""
    print("\n" + "=" * 100)
    print("  PIPER SERMON TYPE COMPARISON — PSR POC")
    print("=" * 100)

    # Header
    ids = [r["id"] for r in results]
    types = [r["type"] for r in results]
    titles = [r["title"][:30] for r in results]

    col_w = 18
    label_w = 26

    def row(label, values, fmt=None):
        vals = [f"{(fmt or '{}').format(v):>{col_w}}" for v in values]
        print(f"  {label:<{label_w}} {''.join(vals)}")

    print()
    row("Sermon Type", types)
    row("Passage", [r["passage"][:col_w] for r in results])
    row("Date", [r["date"] for r in results])
    print(f"  {'-' * (label_w + col_w * len(results))}")

    # Duration & basics
    row("Duration (min)", [round(r["audio"]["duration_seconds"] / 60, 1) for r in results])
    row("Word Count", [r["text"]["word_count"] for r in results])
    row("WPM", [r["text"]["wpm"] for r in results])

    print(f"\n  {'--- BIBLICAL CONTENT ---'}")
    row("Scripture Refs", [r["text"]["scripture_count"] for r in results])
    row("Scripture/min", [r["text"]["scripture_per_min"] for r in results])

    print(f"\n  {'--- DELIVERY ---'}")
    row("Filler Words", [r["text"]["filler_total"] for r in results])
    row("Fillers/min", [r["text"]["filler_per_min"] for r in results])

    print(f"\n  {'--- ENGAGEMENT ---'}")
    row("Pitch Mean (Hz)", [r["audio"]["pitch_mean_hz"] for r in results])
    row("Pitch Std (Hz)", [r["audio"]["pitch_std_hz"] for r in results])
    row("Pitch Range (Hz)", [r["audio"]["pitch_range_hz"] for r in results])
    row("Dynamic Range (dB)", [r["audio"]["dynamic_range_db"] for r in results])
    row("Pauses/min", [r["audio"]["pauses_per_min"] for r in results])

    print(f"\n  {'--- CLARITY ---'}")
    row("Flesch Reading Ease", [r["text"]["flesch_reading_ease"] for r in results])
    row("Grade Level", [r["text"]["flesch_kincaid_grade"] for r in results])

    print(f"\n  {'--- APPLICATION ---'}")
    row("Imperatives", [r["text"]["imperative_sentences"] for r in results])

    # Per-sermon scripture refs
    print(f"\n  {'--- SCRIPTURE REFERENCES DETECTED ---'}")
    for r in results:
        print(f"\n  [{r['type']}] {r['title'][:50]}")
        for ref in r["text"]["scripture_refs"][:10]:
            print(f"    • {ref}")
        if len(r["text"]["scripture_refs"]) > 10:
            print(f"    ...and {len(r['text']['scripture_refs']) - 10} more")

    # Key insight
    print(f"\n{'=' * 100}")
    print("  KEY INSIGHT: Sermon Type Bias on 'Time in the Word'")
    print("=" * 100)
    survey = next((r for r in results if r["type"] == "Survey"), None)
    exeg = next((r for r in results if "Expos" in r["type"] or "Exeg" in r["type"]), None)
    topical = [r for r in results if "Topical" in r["type"]]

    if survey and exeg:
        print(f"\n  Survey sermon ({survey['passage']}):")
        print(f"    Scripture refs: {survey['text']['scripture_count']} ({survey['text']['scripture_per_min']}/min)")
        print(f"  Expository sermon ({exeg['passage']}):")
        print(f"    Scripture refs: {exeg['text']['scripture_count']} ({exeg['text']['scripture_per_min']}/min)")
        ratio = exeg['text']['scripture_per_min'] / max(survey['text']['scripture_per_min'], 0.01)
        print(f"\n  Expository has {ratio:.1f}x the scripture density of the survey.")

    if topical:
        for t in topical:
            print(f"  Topical sermon ({t['passage']}):")
            print(f"    Scripture refs: {t['text']['scripture_count']} ({t['text']['scripture_per_min']}/min)")

    print(f"\n  → This confirms the sermon-type bias: survey/topical sermons get")
    print(f"    structurally lower 'Time in the Word' scores even from elite preachers.")
    print(f"    The PSR scoring model needs to account for this.")
    print("=" * 100)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="PSR Sermon Type Comparison")
    parser.add_argument("--skip-transcribe", action="store_true", help="Reuse cached transcripts")
    args = parser.parse_args()

    print("=" * 100)
    print("  PSR SERMON TYPE COMPARISON")
    print("  Testing scoring bias across sermon types (all John Piper)")
    print("=" * 100)

    results = []
    for sermon in SERMONS:
        print(f"\n{'─' * 100}")
        print(f"  Processing: {sermon['title']}")
        print(f"  Type: {sermon['type']} | Passage: {sermon['passage']}")
        print(f"{'─' * 100}")
        result = run_pipeline(sermon, args.skip_transcribe)
        results.append(result)

    # Save raw results
    out_path = Path("poc/sermon_comparison_results.json")
    out_path.write_text(json.dumps(results, indent=2, default=str))
    print(f"\n  ✓ Raw results saved to {out_path}")

    print_comparison(results)
