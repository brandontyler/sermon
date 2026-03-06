#!/usr/bin/env python3
"""
Generate TTS audio from the bad sermon script using Azure AI Speech REST API.

Usage:
    python3 poc/tts_bad_sermon.py                    # Generate WAV
    python3 poc/tts_bad_sermon.py --voice en-US-GuyNeural  # Different voice
    python3 poc/tts_bad_sermon.py --list-voices      # List available voices

Uses the REST API directly — no SDK install needed.
"""

import argparse
import os
import sys
import requests
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
SCRIPT_PATH = SCRIPT_DIR / "samples" / "bad_sermon_script.txt"
OUTPUT_PATH = SCRIPT_DIR / "samples" / "bad_sermon_mediocre_benchmark.wav"

# Azure Speech TTS REST endpoint pattern
# TTS uses {region}.tts.speech.microsoft.com, not the cognitive services endpoint
REGION = os.environ.get("AZURE_REGION", "eastus2")
TTS_ENDPOINT = f"https://{REGION}.tts.speech.microsoft.com/cognitiveservices/v1"
SPEECH_KEY = os.environ.get("SPEECH_KEY", "")


def list_voices():
    """List available TTS voices for the region."""
    url = f"https://{REGION}.tts.speech.microsoft.com/cognitiveservices/voices/list"
    resp = requests.get(url, headers={"Ocp-Apim-Subscription-Key": SPEECH_KEY})
    resp.raise_for_status()
    voices = resp.json()
    en_us = [v for v in voices if v["Locale"] == "en-US" and "Neural" in v["ShortName"]]
    print(f"Found {len(en_us)} en-US Neural voices:")
    for v in en_us[:20]:
        print(f"  {v['ShortName']:45s} {v['Gender']:8s} {v.get('StyleList', ['default'])[0]}")
    if len(en_us) > 20:
        print(f"  ... and {len(en_us) - 20} more")


def build_ssml(text, voice_name):
    """Wrap text in SSML with a casual, slightly flat delivery."""
    # Slow rate + low pitch variation = mediocre delivery that TTS can produce
    return f"""<speak version='1.0' xmlns='http://www.w3.org/2001/10/synthesis'
       xmlns:mstts='http://www.w3.org/2001/mstts' xml:lang='en-US'>
    <voice name='{voice_name}'>
        <prosody rate='-5%' pitch='-2%'>
            {text}
        </prosody>
    </voice>
</speak>"""


def synthesize(voice_name="en-US-GuyNeural"):
    """Generate WAV from sermon script via Azure TTS REST API."""
    if not SPEECH_KEY:
        print("ERROR: SPEECH_KEY env var not set")
        print("Run: source api/local.settings.json or export SPEECH_KEY=...")
        sys.exit(1)

    script = SCRIPT_PATH.read_text()
    print(f"Script: {len(script)} chars, ~{len(script.split())} words")
    print(f"Voice: {voice_name}")
    print(f"Endpoint: {TTS_ENDPOINT}")

    ssml = build_ssml(script, voice_name)

    headers = {
        "Ocp-Apim-Subscription-Key": SPEECH_KEY,
        "Content-Type": "application/ssml+xml",
        "X-Microsoft-OutputFormat": "riff-24khz-16bit-mono-pcm",
        "User-Agent": "PSR-POC",
    }

    print("Synthesizing... (this may take 30-60s for a long script)")
    resp = requests.post(TTS_ENDPOINT, headers=headers, data=ssml.encode("utf-8"))

    if resp.status_code != 200:
        print(f"ERROR {resp.status_code}: {resp.text[:500]}")
        sys.exit(1)

    OUTPUT_PATH.write_bytes(resp.content)
    size_mb = len(resp.content) / (1024 * 1024)
    # 24kHz 16-bit mono = 48000 bytes/sec
    duration_sec = len(resp.content) / 48000
    print(f"Saved: {OUTPUT_PATH}")
    print(f"Size: {size_mb:.1f} MB")
    print(f"Duration: ~{duration_sec / 60:.1f} min")
    print(f"\nNext: upload to PSR app or run through pipeline POC")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate TTS audio for bad sermon benchmark")
    parser.add_argument("--voice", default="en-US-GuyNeural", help="Azure TTS voice name")
    parser.add_argument("--list-voices", action="store_true", help="List available voices")
    args = parser.parse_args()

    if args.list_voices:
        list_voices()
    else:
        synthesize(args.voice)
