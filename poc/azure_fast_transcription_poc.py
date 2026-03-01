#!/usr/bin/env python3
"""
PSR POC #6 — Azure Fast Transcription API

Tests the fast transcription API (synchronous, up to 2hr/300MB) as a fix
for POC #5's word loss issue (real-time chunking dropped 72% of words).

Questions this POC answers:
  1. Does fast transcription return a complete transcript? (target: ~3,800 words)
  2. How long does it take for a 35-min sermon?
  3. Does scripture formatting work? ("Romans 8:28" vs "Romans 828")

Usage:
    source .venv/bin/activate
    python poc/azure_fast_transcription_poc.py poc/samples/piper_called_according_to_his_purpose.mp3
"""

import argparse
import json
import re
import subprocess
import sys
import time
from pathlib import Path

from azure.core.credentials import AzureKeyCredential
from azure.ai.transcription import TranscriptionClient
from azure.ai.transcription.models import TranscriptionContent, TranscriptionOptions

REGION = "eastus2"
RG = "rg-sermon-rating-dev"
SPEECH_RESOURCE = "psr-speech-dev"


def get_speech_key():
    r = subprocess.run(
        ["az", "cognitiveservices", "account", "keys", "list",
         "--name", SPEECH_RESOURCE, "--resource-group", RG, "--query", "key1", "-o", "tsv"],
        capture_output=True, text=True
    )
    return r.stdout.strip()


def run(audio_path: str):
    print("=" * 60)
    print("  PSR POC #6 — Azure Fast Transcription API")
    print("=" * 60)

    endpoint = f"https://{REGION}.api.cognitive.microsoft.com/"
    key = get_speech_key()

    client = TranscriptionClient(endpoint=endpoint, credential=AzureKeyCredential(key))

    print(f"\n  Audio: {audio_path}")
    file_size_mb = Path(audio_path).stat().st_size / (1024 * 1024)
    print(f"  File size: {file_size_mb:.1f} MB")

    # Transcribe
    print(f"\n[Step 1] Transcribing via Fast Transcription API...")
    t0 = time.time()

    with open(audio_path, "rb") as f:
        options = TranscriptionOptions(locales=["en-US"])
        content = TranscriptionContent(definition=options, audio=f)
        result = client.transcribe(content)

    elapsed = time.time() - t0
    print(f"  ✓ Completed in {elapsed:.1f}s")

    # Extract text
    full_text = result.combined_phrases[0].text if result.combined_phrases else ""
    word_count = len(full_text.split())
    duration_ms = result.duration_milliseconds
    duration_min = duration_ms / 60000
    wpm = round(word_count / duration_min, 1) if duration_min > 0 else 0

    # Scripture reference detection
    scripture_pattern = r'\b(?:Genesis|Exodus|Leviticus|Numbers|Deuteronomy|Joshua|Judges|Ruth|Samuel|Kings|Chronicles|Ezra|Nehemiah|Esther|Job|Psalms?|Proverbs|Ecclesiastes|Song|Isaiah|Jeremiah|Lamentations|Ezekiel|Daniel|Hosea|Joel|Amos|Obadiah|Jonah|Micah|Nahum|Habakkuk|Zephaniah|Haggai|Zechariah|Malachi|Matthew|Mark|Luke|John|Acts|Romans|Corinthians|Galatians|Ephesians|Philippians|Colossians|Thessalonians|Timothy|Titus|Philemon|Hebrews|James|Peter|Jude|Revelation)\s+\d+[:\s]\d+'
    scripture_refs = re.findall(scripture_pattern, full_text, re.IGNORECASE)

    # Phrase count
    phrase_count = len(result.phrases) if result.phrases else 0

    # Build result
    poc_result = {
        "pipeline": "psr-poc6-fast-transcription",
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "source": audio_path,
        "transcription_time_seconds": round(elapsed, 1),
        "duration_milliseconds": duration_ms,
        "duration_minutes": round(duration_min, 1),
        "word_count": word_count,
        "wpm": wpm,
        "phrase_count": phrase_count,
        "scripture_refs_detected": scripture_refs,
        "scripture_ref_count": len(scripture_refs),
        "transcript_preview": full_text[:500],
        "full_text": full_text,
    }

    out_path = Path(__file__).parent / f"fast_transcription_result_{Path(audio_path).stem}.json"
    out_path.write_text(json.dumps(poc_result, indent=2))

    # Print results
    print(f"\n{'=' * 60}")
    print(f"  RESULTS")
    print(f"{'=' * 60}")
    print(f"  Transcription time: {elapsed:.1f}s")
    print(f"  Audio duration:     {duration_min:.1f} min")
    print(f"  Speed ratio:        {duration_min * 60 / elapsed:.1f}x faster than real-time")
    print(f"  Word count:         {word_count}")
    print(f"  WPM:                {wpm}")
    print(f"  Phrases:            {phrase_count}")
    print(f"  Scripture refs:     {len(scripture_refs)}")
    for ref in scripture_refs:
        print(f"    • {ref}")

    # Comparison with previous POCs
    print(f"\n  --- Comparison (same sermon) ---")
    print(f"  {'Metric':<25} {'POC #4 (Whisper)':>18} {'POC #5 (RT chunk)':>18} {'POC #6 (Fast API)':>18}")
    print(f"  {'-'*79}")
    print(f"  {'Words':.<25} {'3,794':>18} {'1,064':>18} {word_count:>18,}")
    print(f"  {'WPM':.<25} {'108.4':>18} {'30.4':>18} {wpm:>18}")
    print(f"  {'Scripture refs (regex)':.<25} {'2':>18} {'N/A':>18} {len(scripture_refs):>18}")
    print(f"  {'Transcription time':.<25} {'~120s':>18} {'~60s':>18} {f'{elapsed:.0f}s':>18}")

    wpm_ok = 80 <= wpm <= 200
    print(f"\n  WPM sanity check: {'✓ PASS' if wpm_ok else '✗ FAIL'} ({wpm} WPM, expected 80-200)")

    print(f"\n  Full results: {out_path}")
    print("=" * 60)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="PSR POC #6 — Azure Fast Transcription API")
    parser.add_argument("audio", help="Path to sermon audio file")
    args = parser.parse_args()
    run(args.audio)
