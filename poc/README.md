# PSR Proof of Concept

Minimal end-to-end pipeline: MP3 → Transcribe → Analyze → Score

## Quick Start

```bash
# Set your OpenAI API key
export OPENAI_API_KEY="sk-..."

# Run with an MP3 file
python3 poc/psr_poc.py path/to/sermon.mp3

# Run in mock mode (no API key needed, uses sample data)
python3 poc/psr_poc.py --mock
```

## What It Does

1. **Transcribe** — Whisper API converts audio to text (swappable to Azure AI Speech later)
2. **Analyze** — GPT-4o analyzes transcript for Delivery metrics (filler words, pacing, structure)
3. **Score** — Produces a PSR Delivery score (0-100) with breakdown

## Output

Writes `psr_result.json` with the full analysis.
