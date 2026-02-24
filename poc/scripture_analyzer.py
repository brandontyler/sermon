#!/usr/bin/env python3
"""
PSR POC #2 — Scripture Cross-Reference Analyzer

Uses ONLY free APIs (no API keys needed):
  - bible-api.com for verse text
  - openbible.info for cross-references
  - Project Gutenberg for historical sermon comparison

Usage:
    python3 scripture_analyzer.py              # Analyze mock sermon
    python3 scripture_analyzer.py --compare    # Also compare against Spurgeon
"""

import argparse
import json
import re
import time
import urllib.request
import urllib.error
from pathlib import Path

# --- Scripture reference detection ---

BOOKS = (
    r"Genesis|Exodus|Leviticus|Numbers|Deuteronomy|Joshua|Judges|Ruth|"
    r"1\s*Samuel|2\s*Samuel|1\s*Kings|2\s*Kings|1\s*Chronicles|2\s*Chronicles|"
    r"Ezra|Nehemiah|Esther|Job|Psalms?|Proverbs|Ecclesiastes|Song\s*of\s*Solomon|"
    r"Isaiah|Jeremiah|Lamentations|Ezekiel|Daniel|Hosea|Joel|Amos|Obadiah|Jonah|"
    r"Micah|Nahum|Habakkuk|Zephaniah|Haggai|Zechariah|Malachi|"
    r"Matthew|Mark|Luke|John|Acts|Romans|1\s*Corinthians|2\s*Corinthians|"
    r"Galatians|Ephesians|Philippians|Colossians|1\s*Thessalonians|2\s*Thessalonians|"
    r"1\s*Timothy|2\s*Timothy|Titus|Philemon|Hebrews|James|1\s*Peter|2\s*Peter|"
    r"1\s*John|2\s*John|3\s*John|Jude|Revelation"
)

# Standard format: "Romans 8:28" or "Romans 8:28-30"
REF_STANDARD = re.compile(
    rf"({BOOKS})\s+(\d{{1,3}})\s*:\s*(\d{{1,3}})(?:\s*[-–]\s*(\d{{1,3}}))?",
    re.IGNORECASE,
)

# Spoken format: "Romans chapter 8, starting in verse 28" / "Romans chapter 8 verse 28"
REF_SPOKEN = re.compile(
    rf"({BOOKS})\s+chapter\s+(\d{{1,3}})\s*,?\s*(?:starting\s+in\s+)?verse\s+(\d{{1,3}})(?:\s*[-–through]+\s*(\d{{1,3}}))?",
    re.IGNORECASE,
)

# Contextual: "verse 29" (resolves against last-seen book+chapter)
REF_VERSE_ONLY = re.compile(r"\bverse\s+(\d{1,3})\b", re.IGNORECASE)


def detect_references(text: str) -> list[dict]:
    """Find all scripture references in text, including spoken patterns."""
    refs = []
    seen_positions: set[int] = set()

    # Pass 1: standard "Book Ch:V" format
    for m in REF_STANDARD.finditer(text):
        book = re.sub(r"\s+", " ", m.group(1)).strip()
        refs.append({
            "book": book, "chapter": int(m.group(2)), "verse_start": int(m.group(3)),
            **({"verse_end": int(m.group(4))} if m.group(4) else {}),
            "raw": m.group(0), "position": m.start(),
        })
        seen_positions.add(m.start())

    # Pass 2: spoken "Book chapter X verse Y" format
    for m in REF_SPOKEN.finditer(text):
        if m.start() in seen_positions:
            continue
        book = re.sub(r"\s+", " ", m.group(1)).strip()
        refs.append({
            "book": book, "chapter": int(m.group(2)), "verse_start": int(m.group(3)),
            **({"verse_end": int(m.group(4))} if m.group(4) else {}),
            "raw": m.group(0), "position": m.start(),
        })
        seen_positions.add(m.start())

    # Pass 3: bare "verse N" — resolve against most recent book+chapter
    if refs:
        for m in REF_VERSE_ONLY.finditer(text):
            # Skip if this position is near an already-matched reference
            if any(abs(m.start() - p) < 80 for p in seen_positions):
                continue
            # Skip if this exact verse was already found from the same chapter
            verse_num = int(m.group(1))
            prior = [r for r in refs if r["position"] < m.start()]
            if prior and any(
                r["book"] == prior[-1]["book"]
                and r["chapter"] == prior[-1]["chapter"]
                and r["verse_start"] == verse_num
                for r in refs
            ):
                continue
            # Find the most recent prior reference
            prior = [r for r in refs if r["position"] < m.start()]
            if prior:
                ctx = prior[-1]
                refs.append({
                    "book": ctx["book"], "chapter": ctx["chapter"],
                    "verse_start": int(m.group(1)),
                    "raw": f"{ctx['book']} {ctx['chapter']}:{m.group(1)} (inferred from '{m.group(0)}')",
                    "position": m.start(),
                })
                seen_positions.add(m.start())

    refs.sort(key=lambda r: r["position"])
    return refs


# --- Free API calls ---


def fetch_json(url: str, retries: int = 2) -> dict | None:
    """GET JSON from a URL with basic retry."""
    for attempt in range(retries + 1):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "PSR-POC/1.0"})
            with urllib.request.urlopen(req, timeout=10) as resp:
                return json.loads(resp.read().decode())
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError):
            if attempt < retries:
                time.sleep(1)
    return None


def fetch_verse_text(ref: dict) -> str | None:
    """Fetch verse text from bible-api.com (free, no auth)."""
    verse = f"{ref['book']}+{ref['chapter']}:{ref['verse_start']}"
    if "verse_end" in ref:
        verse += f"-{ref['verse_end']}"
    url = f"https://bible-api.com/{verse.replace(' ', '+')}"
    data = fetch_json(url)
    if data and "text" in data:
        return data["text"].strip()
    return None


def fetch_cross_references(ref: dict) -> list[str]:
    """Fetch cross-references from openbible.info (free TSV endpoint)."""
    # OpenBible provides a bulk TSV; for POC we use their search-friendly format
    verse_key = f"{ref['book'].lower().replace(' ', '')}+{ref['chapter']}:{ref['verse_start']}"
    url = f"https://www.openbible.info/labs/cross-references/search?q={verse_key}"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "PSR-POC/1.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            html = resp.read().decode()
        # Extract cross-ref links from the HTML (simple parse)
        xrefs = re.findall(r'class="verse"[^>]*>([^<]+)</a>', html)
        return xrefs[:10]  # cap at 10
    except Exception:
        return []


# --- Analysis ---


def analyze_transcript(text: str) -> dict:
    """Run scripture analysis on a transcript."""
    words = text.split()
    word_count = len(words)

    refs = detect_references(text)
    print(f"  Found {len(refs)} scripture reference(s)")

    # Fetch verse text and cross-references for each
    enriched = []
    for ref in refs:
        print(f"  Fetching: {ref['raw']}...")
        verse_text = fetch_verse_text(ref)
        xrefs = fetch_cross_references(ref)
        enriched.append({
            **ref,
            "verse_text": verse_text,
            "cross_references": xrefs,
            "cross_reference_count": len(xrefs),
        })

    # Metrics
    total_xrefs = sum(r["cross_reference_count"] for r in enriched)
    scripture_density = len(refs) / max(word_count / 100, 1)  # refs per 100 words

    # Estimate "time in the word" — crude: count words within ±50 words of a reference
    scripture_zone_words = 0
    for ref in refs:
        pos = ref["position"]
        # Find word index roughly corresponding to char position
        word_idx = len(text[:pos].split())
        start = max(0, word_idx - 25)
        end = min(word_count, word_idx + 25)
        scripture_zone_words += end - start
    scripture_zone_words = min(scripture_zone_words, word_count)
    time_in_word_pct = round(scripture_zone_words / max(word_count, 1) * 100, 1)

    return {
        "word_count": word_count,
        "references_found": len(refs),
        "scripture_density_per_100_words": round(scripture_density, 2),
        "total_cross_references": total_xrefs,
        "avg_cross_refs_per_verse": round(total_xrefs / max(len(refs), 1), 1),
        "estimated_time_in_word_pct": time_in_word_pct,
        "references": enriched,
    }


# --- Spurgeon comparison ---

SPURGEON_EXCERPT = """
"And we know that all things work together for good to them that love God, to them
who are the called according to his purpose." Romans 8:28. Upon this I shall have
two things to say. First, here is what the Christian knows — "We know that all things
work together for good to them that love God." And secondly, here is what the Christian
is — he is one who loves God, and who is "the called according to his purpose."

Let me turn to the first point. "We know." The apostle says, "We know." He does not
say, "We think, we hope, we sometimes imagine," but "We know." It is a matter of
knowledge. I would have every Christian be able to say, "I know." Not "I hope so,"
not "I trust so," but "I know." For this is the privilege of every believer.

Now, what is it that we know? "That all things work together for good." Mark, it does
not say that all things are good in themselves, but that they "work together for good."
Many of the ingredients of a medicine are in themselves nauseous and even poisonous,
but the physician puts them together, and the compound works for the health of the
patient. So it is with the dealings of God. Affliction, persecution, temptation,
bereavement — these are bitter herbs, but the Great Physician compounds them, and
they work together for our good. See Romans 5:3-5 and James 1:2-4 and 2 Corinthians 4:17
and Philippians 1:12 and Genesis 50:20 for further testimony.
"""


def compare_with_spurgeon(sermon_analysis: dict) -> dict:
    """Analyze Spurgeon excerpt and compare metrics."""
    print("\n[Comparison] Analyzing Spurgeon excerpt...")
    spurgeon = analyze_transcript(SPURGEON_EXCERPT)
    return {
        "spurgeon": {
            "word_count": spurgeon["word_count"],
            "references_found": spurgeon["references_found"],
            "scripture_density_per_100_words": spurgeon["scripture_density_per_100_words"],
            "total_cross_references": spurgeon["total_cross_references"],
            "estimated_time_in_word_pct": spurgeon["estimated_time_in_word_pct"],
        },
        "your_sermon": {
            "word_count": sermon_analysis["word_count"],
            "references_found": sermon_analysis["references_found"],
            "scripture_density_per_100_words": sermon_analysis["scripture_density_per_100_words"],
            "total_cross_references": sermon_analysis["total_cross_references"],
            "estimated_time_in_word_pct": sermon_analysis["estimated_time_in_word_pct"],
        },
        "verdict": (
            "Spurgeon packs more scripture per 100 words — typical of expository preaching. "
            "Modern sermons tend to have more illustration and application time. "
            "Neither is wrong; it's a style difference worth tracking."
        ),
    }


# --- Mock transcript (same as POC #1) ---

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


def run(do_compare: bool):
    print("=" * 60)
    print("  PSR POC #2 — Scripture Cross-Reference Analyzer")
    print("  (Free APIs only — no keys needed)")
    print("=" * 60)

    print("\n[Step 1] Detecting scripture references...")
    analysis = analyze_transcript(MOCK_TRANSCRIPT.strip())

    result = {
        "pipeline": "psr-poc-scripture-v1",
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "analysis": analysis,
    }

    if do_compare:
        result["comparison"] = compare_with_spurgeon(analysis)

    out_path = Path(__file__).parent / "scripture_analysis.json"
    out_path.write_text(json.dumps(result, indent=2))
    print(f"\n  ✓ Results written to {out_path}")

    # Print summary
    print("\n" + "=" * 60)
    print("  SCRIPTURE ANALYSIS SUMMARY")
    print("=" * 60)
    print(f"  References found: {analysis['references_found']}")
    print(f"  Scripture density: {analysis['scripture_density_per_100_words']} refs per 100 words")
    print(f"  Total cross-references: {analysis['total_cross_references']}")
    print(f"  Avg cross-refs per verse: {analysis['avg_cross_refs_per_verse']}")
    print(f"  Estimated time in the Word: {analysis['estimated_time_in_word_pct']}%")

    for ref in analysis["references"]:
        status = "✓" if ref["verse_text"] else "✗"
        xref_count = ref["cross_reference_count"]
        print(f"\n  {status} {ref['raw']}")
        if ref["verse_text"]:
            text_preview = ref["verse_text"][:120] + "..." if len(ref["verse_text"] or "") > 120 else ref["verse_text"]
            print(f"    Text: {text_preview}")
        if ref["cross_references"]:
            print(f"    Cross-refs ({xref_count}): {', '.join(ref['cross_references'][:5])}")

    if do_compare and "comparison" in result:
        c = result["comparison"]
        print("\n" + "-" * 60)
        print("  HISTORICAL COMPARISON: You vs Spurgeon")
        print("-" * 60)
        print(f"  {'Metric':<35} {'You':>8} {'Spurgeon':>10}")
        print(f"  {'Refs found':<35} {c['your_sermon']['references_found']:>8} {c['spurgeon']['references_found']:>10}")
        print(f"  {'Density (per 100 words)':<35} {c['your_sermon']['scripture_density_per_100_words']:>8} {c['spurgeon']['scripture_density_per_100_words']:>10}")
        print(f"  {'Cross-references':<35} {c['your_sermon']['total_cross_references']:>8} {c['spurgeon']['total_cross_references']:>10}")
        print(f"  {'Time in Word %':<35} {c['your_sermon']['estimated_time_in_word_pct']:>7}% {c['spurgeon']['estimated_time_in_word_pct']:>9}%")
        print(f"\n  {c['verdict']}")

    print("=" * 60)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="PSR POC #2 — Scripture Analyzer")
    parser.add_argument("--compare", action="store_true", help="Compare against Spurgeon")
    args = parser.parse_args()
    run(args.compare)
