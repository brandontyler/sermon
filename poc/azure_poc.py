#!/usr/bin/env python3
"""
Azure POC — Validate Azure AI Speech transcription + Azure OpenAI analysis.

Tests:
  1. Azure AI Speech: transcribe sermon audio with timestamps
  2. Azure OpenAI (GPT-4o): score the transcript on PSR delivery metrics

Requires env vars (or set in .env):
  AZURE_SPEECH_KEY, AZURE_SPEECH_REGION
  AZURE_OPENAI_KEY, AZURE_OPENAI_ENDPOINT, AZURE_OPENAI_DEPLOYMENT

Usage:
    python3 poc/azure_poc.py poc/samples/piper_romans_1_8.mp3
    python3 poc/azure_poc.py poc/samples/piper_romans_1_8.mp3 --duration 120
"""

import json, sys, time, os, subprocess, tempfile
from pathlib import Path

SPEECH_KEY = os.environ.get("AZURE_SPEECH_KEY", "")
SPEECH_REGION = os.environ.get("AZURE_SPEECH_REGION", "eastus2")
OPENAI_KEY = os.environ.get("AZURE_OPENAI_KEY", "")
OPENAI_ENDPOINT = os.environ.get("AZURE_OPENAI_ENDPOINT", "https://eastus2.api.cognitive.microsoft.com/")
OPENAI_DEPLOYMENT = os.environ.get("AZURE_OPENAI_DEPLOYMENT", "gpt-4o")


def to_wav(audio_path: str, duration: int = 120) -> str:
    """Convert audio to 16kHz mono WAV (required by Speech SDK). Returns temp path."""
    tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
    tmp.close()
    subprocess.run([
        "ffmpeg", "-i", audio_path, "-t", str(duration),
        "-ar", "16000", "-ac", "1", "-f", "wav", tmp.name, "-y"
    ], capture_output=True, check=True)
    return tmp.name


def test_speech(audio_path: str, duration: int) -> str:
    """Transcribe audio via Azure AI Speech with continuous recognition."""
    import azure.cognitiveservices.speech as speechsdk

    print("\n[Test 1] Azure AI Speech — Transcription")
    print(f"  File: {audio_path} (first {duration}s)")

    wav_path = to_wav(audio_path, duration)
    try:
        config = speechsdk.SpeechConfig(subscription=SPEECH_KEY, region=SPEECH_REGION)
        config.request_word_level_timestamps()
        audio = speechsdk.AudioConfig(filename=wav_path)
        recognizer = speechsdk.SpeechRecognizer(speech_config=config, audio_config=audio)

        results, done = [], False
        recognizer.recognized.connect(
            lambda evt: results.append(evt.result.text)
            if evt.result.reason == speechsdk.ResultReason.RecognizedSpeech else None
        )
        recognizer.session_stopped.connect(lambda evt: done_setter())
        recognizer.canceled.connect(lambda evt: done_setter())

        def done_setter():
            nonlocal done
            done = True

        start = time.time()
        recognizer.start_continuous_recognition()
        while not done:
            time.sleep(0.5)
        recognizer.stop_continuous_recognition()

        transcript = " ".join(results)
        print(f"  ✓ Transcribed {len(transcript.split())} words in {time.time()-start:.1f}s")
        print(f"  Preview: {transcript[:300]}...")
        return transcript
    finally:
        os.unlink(wav_path)


def test_openai(transcript: str) -> dict:
    """Score transcript via Azure OpenAI GPT-4o."""
    from openai import AzureOpenAI

    print("\n[Test 2] Azure OpenAI (GPT-4o) — PSR Analysis")

    client = AzureOpenAI(
        api_key=OPENAI_KEY,
        api_version="2024-12-01-preview",
        azure_endpoint=OPENAI_ENDPOINT,
    )

    chunk = " ".join(transcript.split()[:2000])
    start = time.time()
    resp = client.chat.completions.create(
        model=OPENAI_DEPLOYMENT,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": (
                "You are a sermon analytics engine. Analyze the transcript and return JSON:\n"
                '{"delivery_score": 0-100, "filler_words": {"um": N, ...}, '
                '"scripture_refs": ["ref", ...], '
                '"segment_breakdown": {"scripture": %, "teaching": %, "anecdote": %, "application": %, "other": %}, '
                '"strengths": ["..."], "improvements": ["..."], '
                '"summary": "2-3 sentences"}'
            )},
            {"role": "user", "content": f"Analyze this sermon transcript:\n\n{chunk}"},
        ],
    )

    result = json.loads(resp.choices[0].message.content)
    usage = resp.usage
    print(f"  ✓ Analysis complete in {time.time()-start:.1f}s")
    print(f"  Tokens: {usage.prompt_tokens} in / {usage.completion_tokens} out")
    print(f"  Delivery score: {result.get('delivery_score')}/100")
    print(f"  Scripture refs: {result.get('scripture_refs')}")
    print(f"  Summary: {result.get('summary')}")
    return result


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Azure POC — Speech + OpenAI")
    parser.add_argument("audio", help="Path to audio file (MP3/WAV/M4A)")
    parser.add_argument("--duration", type=int, default=120, help="Seconds to transcribe (default: 120)")
    args = parser.parse_args()

    if not Path(args.audio).exists():
        print(f"File not found: {args.audio}")
        sys.exit(1)

    for var, name in [(SPEECH_KEY, "AZURE_SPEECH_KEY"), (OPENAI_KEY, "AZURE_OPENAI_KEY")]:
        if not var:
            print(f"Missing env var: {name}")
            sys.exit(1)

    print("=" * 60)
    print("  Azure POC — Speech + OpenAI Smoke Test")
    print("=" * 60)

    transcript = test_speech(args.audio, args.duration)
    analysis = test_openai(transcript)

    out = Path("poc/azure_poc_result.json")
    out.write_text(json.dumps({
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "audio": args.audio,
        "duration_tested": args.duration,
        "transcript_words": len(transcript.split()),
        "transcript_preview": transcript[:500],
        "analysis": analysis,
    }, indent=2))

    print(f"\n  ✓ Results saved to {out}")
    print("=" * 60)
    print("  BOTH AZURE SERVICES WORKING ✓")
    print("=" * 60)
