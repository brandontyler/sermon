#!/usr/bin/env python3
"""PSR E2E Integration Test — Upload through deployed pipeline.

Uploads a real sermon, polls until complete, validates the full document.

Usage:
    python tests/e2e-integration.py                          # default: Piper sample
    python tests/e2e-integration.py --file path/to/sermon.mp3
    API_BASE=https://psr-functions-dev.azurewebsites.net python tests/e2e-integration.py
"""

import argparse
import os
import sys
import time

import requests

API_BASE = os.environ.get("API_BASE", "https://psr-functions-dev.azurewebsites.net")
DEFAULT_FILE = "poc/samples/piper_called_according_to_his_purpose.mp3"
POLL_INTERVAL = 15  # seconds
POLL_TIMEOUT = 600  # 10 minutes (transcription + 5 LLM passes + cold starts)

ALL_CATEGORIES = [
    "biblicalAccuracy", "timeInTheWord", "passageFocus", "clarity",
    "engagement", "application", "delivery", "emotionalRange",
]

passed = 0
failed = 0


def check(name, condition, detail=""):
    global passed, failed
    if condition:
        passed += 1
        print(f"  ✅ {name}" + (f" — {detail}" if detail else ""))
    else:
        failed += 1
        print(f"  ❌ {name}" + (f" — {detail}" if detail else ""))


def main():
    global passed, failed
    parser = argparse.ArgumentParser()
    parser.add_argument("--file", default=DEFAULT_FILE, help="Audio file to upload")
    parser.add_argument("--skip-upload", metavar="ID", help="Skip upload, poll existing sermon ID")
    args = parser.parse_args()

    url = f"{API_BASE}/api/sermons"

    # ── Step 1: Upload ──
    if args.skip_upload:
        sermon_id = args.skip_upload
        print(f"\n⏭  Skipping upload, using existing sermon: {sermon_id}")
    else:
        if not os.path.exists(args.file):
            print(f"❌ File not found: {args.file}")
            sys.exit(1)

        size_mb = os.path.getsize(args.file) / (1024 * 1024)
        print(f"\n📤 Uploading {os.path.basename(args.file)} ({size_mb:.1f} MB) to {url}")

        with open(args.file, "rb") as f:
            resp = requests.post(url, files={"file": (os.path.basename(args.file), f, "audio/mpeg")}, timeout=120)

        check("Upload returns 202", resp.status_code == 202, f"got {resp.status_code}")
        if resp.status_code != 202:
            print(f"  Response: {resp.text[:300]}")
            sys.exit(1)

        body = resp.json()
        sermon_id = body.get("id")
        check("Upload returns sermon ID", sermon_id is not None, sermon_id)
        check("Upload returns processing status", body.get("status") == "processing")

    # ── Step 2: Poll until complete ──
    detail_url = f"{url}/{sermon_id}"
    print(f"\n⏳ Polling {detail_url} (timeout {POLL_TIMEOUT}s)")

    start = time.time()
    doc = None
    while time.time() - start < POLL_TIMEOUT:
        try:
            resp = requests.get(detail_url, timeout=30)
            if resp.status_code == 200:
                doc = resp.json()
                status = doc.get("status")
                elapsed = int(time.time() - start)
                if status == "complete":
                    print(f"  ✅ Complete after {elapsed}s")
                    break
                elif status == "failed":
                    print(f"  ❌ Pipeline failed after {elapsed}s: {doc.get('error', '?')}")
                    sys.exit(1)
                else:
                    print(f"  ⏳ {status}... ({elapsed}s)")
        except requests.RequestException as e:
            print(f"  ⚠️  Request error (cold start?): {e}")
        time.sleep(POLL_INTERVAL)
    else:
        print(f"  ❌ Timed out after {POLL_TIMEOUT}s")
        sys.exit(1)

    # ── Step 3: Validate sermon document ──
    print(f"\n🔍 Validating sermon document")

    check("Status is complete", doc["status"] == "complete")
    check("Has title", bool(doc.get("title")))
    check("Has pastor field", "pastor" in doc, doc.get("pastor") or "(null — not detected in transcript)")
    check("Has duration (seconds)", isinstance(doc.get("duration"), (int, float)) and doc["duration"] > 0, f"{doc.get('duration')}s")
    check("Has sermon type", doc.get("sermonType") in ("expository", "topical", "survey"), doc.get("sermonType"))

    # Composite PSR
    composite = doc.get("compositePsr")
    check("Has composite PSR", isinstance(composite, (int, float)) and 0 < composite <= 100, composite)
    check("Composite in expected range (75-95)", 75 <= (composite or 0) <= 95, f"PSR={composite}")

    # All 8 categories
    cats = doc.get("categories", {})
    check("Has categories object", isinstance(cats, dict))
    for cat in ALL_CATEGORIES:
        entry = cats.get(cat, {})
        score = entry.get("score")
        reasoning = entry.get("reasoning")
        check(f"  {cat}: score", isinstance(score, (int, float)) and 0 <= score <= 100, score)
        check(f"  {cat}: reasoning", isinstance(reasoning, str) and len(reasoning) > 10)

    # Summary, strengths, improvements
    check("Has summary", isinstance(doc.get("summary"), str) and len(doc["summary"]) > 10)
    check("Has strengths (3)", isinstance(doc.get("strengths"), list) and len(doc["strengths"]) == 3)
    check("Has improvements (2-3)", isinstance(doc.get("improvements"), list) and 2 <= len(doc.get("improvements", [])) <= 3)

    # Transcript
    transcript = doc.get("transcript", {})
    check("Has transcript.fullText", isinstance(transcript.get("fullText"), str) and len(transcript["fullText"]) > 500)
    segments = transcript.get("segments", [])
    check("Has transcript segments", isinstance(segments, list) and len(segments) > 10, f"{len(segments)} segments")
    if segments:
        seg = segments[0]
        check("Segments have start/end/text/type", all(k in seg for k in ("start", "end", "text", "type")))
        types_found = set(s.get("type") for s in segments)
        check("Multiple segment types classified", len(types_found) > 1, types_found)

    # Classification metadata
    check("Has classificationConfidence", isinstance(doc.get("classificationConfidence"), (int, float)))
    check("Has normalizationApplied", doc.get("normalizationApplied") in ("none", "half", "full"))

    # Audio metrics (should be present for audio uploads)
    if not args.skip_upload:
        audio = doc.get("audioMetrics")
        check("Has audioMetrics", isinstance(audio, dict))
        if audio:
            check("  pitchMeanHz > 0", (audio.get("pitchMeanHz") or 0) > 0)
            check("  durationSeconds > 0", (audio.get("durationSeconds") or 0) > 0)

    # ── Step 4: Verify feed list includes this sermon ──
    print(f"\n📋 Verifying feed list")
    resp = requests.get(url, timeout=30)
    check("GET /api/sermons returns 200", resp.status_code == 200)
    feed = resp.json()
    check("Feed is a list", isinstance(feed, list))
    ids_in_feed = [s.get("id") for s in feed]
    check("Sermon appears in feed", sermon_id in ids_in_feed)
    feed_entry = next((s for s in feed if s["id"] == sermon_id), {})
    check("Feed entry has compositePsr", isinstance(feed_entry.get("compositePsr"), (int, float)))
    check("Feed entry has title", bool(feed_entry.get("title")))

    # ── Summary ──
    print(f"\n{'═' * 50}")
    print(f"  {passed} PASSED, {failed} FAILED out of {passed + failed}")
    print(f"  Sermon: {sermon_id}")
    print(f"  PSR: {composite} | Type: {doc.get('sermonType')} | Duration: {doc.get('duration')}s")
    print(f"{'═' * 50}")

    sys.exit(1 if failed > 0 else 0)


if __name__ == "__main__":
    main()
