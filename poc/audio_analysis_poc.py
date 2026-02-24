#!/usr/bin/env python3
"""
PSR POC #3 — Open-Source Audio + Text Analysis

Analyzes a sermon audio file using ONLY free, local tools (no API keys):
  - faster-whisper: local transcription with word timestamps
  - Parselmouth (Praat): pitch, intensity, pauses from audio
  - textstat: readability scores
  - spaCy: sentence structure, imperative detection, filler words

Usage:
    source .venv/bin/activate
    python poc/audio_analysis_poc.py poc/samples/piper_romans_1_8.mp3
    python poc/audio_analysis_poc.py poc/samples/piper_romans_1_8.mp3 --skip-transcribe  # reuse cached transcript
"""

import argparse
import json
import re
import time
from pathlib import Path

import numpy as np


# --- Transcription (faster-whisper, local) ---

def transcribe(audio_path: str, cache_path: Path) -> dict:
    """Transcribe with faster-whisper (runs locally, no API key)."""
    if cache_path.exists():
        print("  Using cached transcript")
        return json.loads(cache_path.read_text())

    from faster_whisper import WhisperModel
    print("  Loading whisper model (first run downloads ~1.5GB)...")
    model = WhisperModel("base", compute_type="int8", device="cpu")
    print(f"  Transcribing {audio_path}...")
    segments, info = model.transcribe(audio_path, word_timestamps=True)

    words = []
    full_text_parts = []
    for seg in segments:
        full_text_parts.append(seg.text)
        for w in (seg.words or []):
            words.append({"word": w.word.strip(), "start": round(w.start, 2), "end": round(w.end, 2)})

    result = {
        "text": " ".join(full_text_parts).strip(),
        "words": words,
        "duration": round(info.duration, 1),
        "language": info.language,
    }
    cache_path.write_text(json.dumps(result, indent=2))
    print(f"  ✓ {len(words)} words, {info.duration:.0f}s")
    return result


# --- Audio analysis (Parselmouth) ---

def analyze_audio(audio_path: str) -> dict:
    """Extract pitch, intensity, and pause metrics from audio."""
    import parselmouth

    snd = parselmouth.Sound(audio_path)
    pitch = snd.to_pitch(time_step=0.1)
    intensity = snd.to_intensity(time_step=0.1)

    pitch_values = pitch.selected_array["frequency"]
    pitch_voiced = pitch_values[pitch_values > 0]
    intensity_values = intensity.values[0]

    # Pause detection: stretches where intensity drops below threshold
    threshold = np.percentile(intensity_values, 20)
    silent_frames = intensity_values < threshold
    # Count transitions from voiced to silent
    transitions = np.diff(silent_frames.astype(int))
    pause_count = int(np.sum(transitions == 1))

    return {
        "pitch": {
            "mean_hz": round(float(np.mean(pitch_voiced)), 1) if len(pitch_voiced) > 0 else 0,
            "std_hz": round(float(np.std(pitch_voiced)), 1) if len(pitch_voiced) > 0 else 0,
            "min_hz": round(float(np.min(pitch_voiced)), 1) if len(pitch_voiced) > 0 else 0,
            "max_hz": round(float(np.max(pitch_voiced)), 1) if len(pitch_voiced) > 0 else 0,
            "range_hz": round(float(np.max(pitch_voiced) - np.min(pitch_voiced)), 1) if len(pitch_voiced) > 0 else 0,
        },
        "intensity": {
            "mean_db": round(float(np.mean(intensity_values)), 1),
            "std_db": round(float(np.std(intensity_values)), 1),
            "dynamic_range_db": round(float(np.max(intensity_values) - np.min(intensity_values)), 1),
        },
        "pauses": {
            "count": pause_count,
            "per_minute": round(pause_count / (snd.duration / 60), 1),
        },
        "duration_seconds": round(snd.duration, 1),
    }


# --- Text analysis ---

FILLER_PATTERNS = re.compile(
    r"\b(um|uh|uh huh|you know|like|so|right|i mean|basically|actually|literally)\b",
    re.IGNORECASE,
)


def analyze_text(text: str, duration_seconds: float) -> dict:
    """Readability, filler words, structure, scripture refs."""
    import spacy
    import textstat

    nlp = spacy.load("en_core_web_sm")
    doc = nlp(text)

    words = text.split()
    word_count = len(words)
    sentence_count = len(list(doc.sents))
    wpm = round(word_count / (duration_seconds / 60), 1)

    # Filler words
    fillers = {}
    for m in FILLER_PATTERNS.finditer(text.lower()):
        w = m.group(1)
        fillers[w] = fillers.get(w, 0) + 1
    filler_total = sum(fillers.values())

    # Imperatives (application moments)
    imperative_count = 0
    for sent in doc.sents:
        tokens = [t for t in sent if not t.is_space]
        if tokens and tokens[0].pos_ == "VERB" and tokens[0].dep_ == "ROOT":
            imperative_count += 1

    # Scripture references — enhanced for spoken transcripts
    # Whisper transcripts say "chapter 3 verse 21" without repeating the book name.
    # We detect "chapter X verse Y" and resolve the book from surrounding context.
    import sys
    sys.path.insert(0, str(Path(__file__).parent))
    from scripture_analyzer import detect_references, BOOKS

    refs = detect_references(text)

    # Also catch standalone "chapter X verse Y" patterns (no book prefix)
    chv_pattern = re.compile(
        r"chapter\s+(\d{1,3})\s*,?\s*(?:starting\s+in\s+)?verse\s+(\d{1,3})(?:\s*[-–to]+\s*(\d{1,3}))?",
        re.IGNORECASE,
    )
    book_pattern = re.compile(rf"\b({BOOKS})\b", re.IGNORECASE)
    ref_positions = {r["position"] for r in refs}

    for m in chv_pattern.finditer(text):
        if any(abs(m.start() - p) < 60 for p in ref_positions):
            continue
        # Find most recent book name before this position
        last_book = None
        for bm in book_pattern.finditer(text[:m.start()]):
            last_book = re.sub(r"\s+", " ", bm.group(1)).strip()
        if last_book:
            refs.append({
                "book": last_book,
                "chapter": int(m.group(1)),
                "verse_start": int(m.group(2)),
                "raw": f"{last_book} {m.group(1)}:{m.group(2)} (from '{m.group(0).strip()}')",
                "position": m.start(),
            })
            ref_positions.add(m.start())

    refs.sort(key=lambda r: r["position"])

    return {
        "word_count": word_count,
        "sentence_count": sentence_count,
        "words_per_minute": wpm,
        "readability": {
            "flesch_reading_ease": round(textstat.flesch_reading_ease(text), 1),
            "flesch_kincaid_grade": round(textstat.flesch_kincaid_grade(text), 1),
            "gunning_fog": round(textstat.gunning_fog(text), 1),
            "smog_index": round(textstat.smog_index(text), 1),
            "dale_chall": round(textstat.dale_chall_readability_score(text), 1),
        },
        "filler_words": fillers,
        "filler_total": filler_total,
        "filler_per_minute": round(filler_total / (duration_seconds / 60), 1),
        "imperative_sentences": imperative_count,
        "scripture_references": [r["raw"] for r in refs],
        "scripture_count": len(refs),
        "scripture_per_minute": round(len(refs) / (duration_seconds / 60), 2),
    }


# --- Main ---

def run(audio_path: str, skip_transcribe: bool):
    print("=" * 60)
    print("  PSR POC #3 — Open-Source Audio + Text Analysis")
    print("  (No API keys needed — everything runs locally)")
    print("=" * 60)

    poc_dir = Path(__file__).parent
    cache_path = poc_dir / "transcript_cache.json"

    # Step 1: Transcribe
    print("\n[Step 1] Transcription (faster-whisper, local)")
    if skip_transcribe and cache_path.exists():
        transcript = json.loads(cache_path.read_text())
        print(f"  ✓ Loaded cached transcript: {len(transcript['words'])} words")
    else:
        transcript = transcribe(audio_path, cache_path)

    # Step 2: Audio analysis
    print("\n[Step 2] Audio Analysis (Parselmouth)")
    audio = analyze_audio(audio_path)
    print(f"  ✓ Pitch: {audio['pitch']['mean_hz']}Hz mean, {audio['pitch']['std_hz']}Hz std")
    print(f"  ✓ Intensity: {audio['intensity']['mean_db']}dB mean, {audio['intensity']['dynamic_range_db']}dB range")
    print(f"  ✓ Pauses: {audio['pauses']['count']} detected ({audio['pauses']['per_minute']}/min)")

    # Step 3: Text analysis
    print("\n[Step 3] Text Analysis (textstat + spaCy)")
    text = analyze_text(transcript["text"], transcript["duration"])
    print(f"  ✓ Readability: Flesch {text['readability']['flesch_reading_ease']}, Grade {text['readability']['flesch_kincaid_grade']}")
    print(f"  ✓ Fillers: {text['filler_total']} total ({text['filler_per_minute']}/min)")
    print(f"  ✓ Scripture refs: {text['scripture_count']} ({text['scripture_per_minute']}/min)")

    # Build result
    result = {
        "pipeline": "psr-poc-audio-v1",
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "source": audio_path,
        "sermon_info": {
            "title": "The Mighty and Merciful Message of Romans 1-8",
            "preacher": "John Piper",
            "date": "2002-09-22",
            "source_url": "https://www.desiringgod.org/messages/the-mighty-and-merciful-message-of-romans-1-8",
        },
        "audio_analysis": audio,
        "text_analysis": text,
    }

    out_path = poc_dir / "audio_analysis_result.json"
    out_path.write_text(json.dumps(result, indent=2))

    # Print scorecard
    print("\n" + "=" * 60)
    print(f"  SERMON ANALYSIS: {result['sermon_info']['preacher']}")
    print(f"  \"{result['sermon_info']['title']}\"")
    print("=" * 60)
    print(f"\n  Duration:        {audio['duration_seconds'] / 60:.1f} minutes")
    print(f"  Words:           {text['word_count']:,}")
    print(f"  WPM:             {text['words_per_minute']}")
    print(f"\n  --- DELIVERY ---")
    print(f"  Filler words:    {text['filler_total']} ({text['filler_per_minute']}/min)")
    if text['filler_words']:
        top = sorted(text['filler_words'].items(), key=lambda x: -x[1])[:5]
        print(f"  Top fillers:     {', '.join(f'{w}({c})' for w, c in top)}")
    print(f"\n  --- ENGAGEMENT ---")
    print(f"  Pitch range:     {audio['pitch']['range_hz']}Hz ({audio['pitch']['min_hz']}-{audio['pitch']['max_hz']}Hz)")
    print(f"  Pitch variation: {audio['pitch']['std_hz']}Hz std (higher = more dynamic)")
    print(f"  Volume range:    {audio['intensity']['dynamic_range_db']}dB")
    print(f"  Pauses:          {audio['pauses']['count']} ({audio['pauses']['per_minute']}/min)")
    print(f"\n  --- CLARITY ---")
    print(f"  Flesch Reading:  {text['readability']['flesch_reading_ease']} (higher = easier)")
    print(f"  Grade Level:     {text['readability']['flesch_kincaid_grade']}")
    print(f"  Gunning Fog:     {text['readability']['gunning_fog']}")
    print(f"\n  --- BIBLICAL CONTENT ---")
    print(f"  Scripture refs:  {text['scripture_count']} ({text['scripture_per_minute']}/min)")
    print(f"  Imperatives:     {text['imperative_sentences']} (application moments)")
    if text['scripture_references']:
        print(f"  References:      {', '.join(text['scripture_references'][:10])}")
        if len(text['scripture_references']) > 10:
            print(f"                   ...and {len(text['scripture_references']) - 10} more")
    print("\n" + "=" * 60)
    print(f"  Full results: {out_path}")
    print("=" * 60)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="PSR POC #3 — Audio Analysis")
    parser.add_argument("audio", help="Path to sermon audio file (MP3, WAV, etc.)")
    parser.add_argument("--skip-transcribe", action="store_true", help="Reuse cached transcript")
    args = parser.parse_args()
    run(args.audio, args.skip_transcribe)
