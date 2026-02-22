#!/usr/bin/env python3
"""
PSR Proof of Concept — End-to-end sermon analysis pipeline.

Usage:
    python3 psr_poc.py path/to/sermon.mp3          # Full pipeline with OpenAI
    python3 psr_poc.py --mock                       # Mock mode, no API needed
"""

import argparse
import json
import os
import sys
import time
from pathlib import Path

MOCK_TRANSCRIPT = """
Good morning church, welcome welcome. Um, it's so good to see everyone here today.
I want to, uh, talk to you about something that's been on my heart. If you have your
Bibles, turn with me to Romans chapter 8, starting in verse 28. And we know that in
all things God works for the good of those who love him, who have been called according
to his purpose. You know, this is one of those verses that, like, we hear all the time,
but do we really understand what Paul is saying here?

See, Paul isn't saying that everything that happens is good. He's saying God works IN
all things. There's a difference, right? Um, let me give you an example. When I was
going through a really tough season about five years ago, I remember sitting in my car
just, you know, wondering if God even cared. And I opened my Bible to this exact passage.
And it hit me differently that day.

The word "works" here in the Greek is "synergeo" — it's where we get our word "synergy."
God is actively working, cooperating with circumstances, to produce good. Not passive.
Not distant. Active. And the scope is "all things" — not some things, not the easy things.
ALL things. That includes your worst day. That includes, uh, the diagnosis you just got.
That includes the relationship that fell apart.

Now look at verse 29 — "For those God foreknew he also predestined to be conformed to
the image of his Son." The goal isn't comfort. The goal is Christlikeness. God's definition
of "good" in verse 28 is defined by verse 29. He's making you look like Jesus. And sometimes
that process, like, it hurts. But it's good.

So here's my challenge to you this morning. This week, when something hard happens — and it
will — I want you to pause and say, "God is working in this." Not "God caused this." Not
"this is fine." But "God is actively working in this for my good, and His good is making me
more like Christ." Can you do that? Let's pray.
"""


def transcribe(audio_path: str) -> dict:
    """Transcribe audio via OpenAI Whisper API."""
    from openai import OpenAI

    client = OpenAI()
    print(f"  Transcribing {audio_path}...")
    with open(audio_path, "rb") as f:
        result = client.audio.transcriptions.create(
            model="whisper-1",
            file=f,
            response_format="verbose_json",
            timestamp_granularities=["segment"],
        )
    return {
        "text": result.text,
        "duration": result.duration,
        "segments": [
            {"start": s.start, "end": s.end, "text": s.text}
            for s in (result.segments or [])
        ],
    }


def analyze(transcript_text: str) -> dict:
    """Analyze transcript for PSR Delivery score via GPT-4o."""
    from openai import OpenAI

    client = OpenAI()
    print("  Analyzing transcript for PSR Delivery score...")
    resp = client.chat.completions.create(
        model="gpt-4o",
        response_format={"type": "json_object"},
        messages=[
            {
                "role": "system",
                "content": (
                    "You are a sermon analytics engine. Analyze the transcript and return JSON with:\n"
                    '- "delivery_score": 0-100 integer\n'
                    '- "filler_words": object mapping each filler word to its count\n'
                    '- "filler_total": total filler word count\n'
                    '- "estimated_wpm": words per minute estimate\n'
                    '- "scripture_refs": list of scripture references found (e.g. "Romans 8:28")\n'
                    '- "segment_types": object with percentage breakdown: scripture_reading, teaching, anecdote, application, prayer, other\n'
                    '- "strengths": list of 2-3 delivery strengths\n'
                    '- "improvements": list of 2-3 areas to improve\n'
                    '- "summary": 2-3 sentence overall assessment\n'
                    "Be objective and data-driven. Base filler word counts on actual occurrences in the text."
                ),
            },
            {"role": "user", "content": f"Analyze this sermon transcript:\n\n{transcript_text}"},
        ],
    )
    return json.loads(resp.choices[0].message.content)


def mock_analyze(transcript_text: str) -> dict:
    """Mock analysis for demo without API."""
    words = transcript_text.split()
    filler_map = {"um": 0, "uh": 0, "you know": 0, "like": 0, "right": 0}
    text_lower = transcript_text.lower()
    for filler in filler_map:
        filler_map[filler] = text_lower.count(filler)
    return {
        "delivery_score": 74,
        "filler_words": filler_map,
        "filler_total": sum(filler_map.values()),
        "estimated_wpm": 138,
        "scripture_refs": ["Romans 8:28", "Romans 8:29"],
        "segment_types": {
            "scripture_reading": 0.10,
            "teaching": 0.40,
            "anecdote": 0.20,
            "application": 0.15,
            "prayer": 0.05,
            "other": 0.10,
        },
        "strengths": [
            "Good use of Greek word study (synergeo)",
            "Clear call to action at the end",
            "Effective personal anecdote",
        ],
        "improvements": [
            "Reduce filler words (um, uh, like, you know) — 15+ occurrences",
            "Could spend more time in the actual text vs illustration",
            "Vary pacing — delivery feels consistent throughout",
        ],
        "summary": (
            "Solid sermon with strong biblical grounding in Romans 8:28-29. "
            "The Greek word study adds depth. Main area for improvement is filler word "
            "frequency which slightly undermines delivery confidence."
        ),
    }


def run(audio_path: str | None, mock: bool):
    print("=" * 60)
    print("  PSR Proof of Concept — Sermon Analysis Pipeline")
    print("=" * 60)

    # Step 1: Transcribe
    print("\n[Step 1] Transcription")
    if mock:
        print("  Using mock transcript (no API call)")
        transcript = {"text": MOCK_TRANSCRIPT.strip(), "duration": 240, "segments": []}
    else:
        if not audio_path or not Path(audio_path).exists():
            print(f"  ERROR: File not found: {audio_path}")
            sys.exit(1)
        transcript = transcribe(audio_path)

    word_count = len(transcript["text"].split())
    print(f"  ✓ Transcript: {word_count} words, ~{transcript['duration']:.0f}s duration")

    # Step 2: Analyze
    print("\n[Step 2] PSR Analysis")
    if mock:
        print("  Using mock analysis (no API call)")
        analysis = mock_analyze(transcript["text"])
    else:
        analysis = analyze(transcript["text"])

    # Step 3: Build result
    print("\n[Step 3] Results")
    result = {
        "pipeline": "psr-poc-v1",
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "source": audio_path or "mock",
        "transcript": {
            "text": transcript["text"],
            "word_count": word_count,
            "duration_seconds": transcript["duration"],
        },
        "psr": analysis,
    }

    out_path = Path(__file__).parent / "psr_result.json"
    out_path.write_text(json.dumps(result, indent=2))
    print(f"  ✓ Full result written to {out_path}")

    # Print summary
    print("\n" + "=" * 60)
    print(f"  PSR DELIVERY SCORE: {analysis['delivery_score']}/100")
    print("=" * 60)
    print(f"  Filler words: {analysis['filler_total']} total — {analysis['filler_words']}")
    print(f"  WPM: ~{analysis['estimated_wpm']}")
    print(f"  Scripture refs: {', '.join(analysis['scripture_refs'])}")
    print(f"\n  Strengths:")
    for s in analysis["strengths"]:
        print(f"    ✓ {s}")
    print(f"\n  Improvements:")
    for i in analysis["improvements"]:
        print(f"    → {i}")
    print(f"\n  Summary: {analysis['summary']}")
    print("=" * 60)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="PSR Proof of Concept")
    parser.add_argument("audio", nargs="?", help="Path to MP3/audio file")
    parser.add_argument("--mock", action="store_true", help="Run with mock data (no API)")
    args = parser.parse_args()

    if not args.mock and not args.audio:
        parser.error("Provide an audio file path, or use --mock")

    run(args.audio, args.mock)
