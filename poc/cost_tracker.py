#!/usr/bin/env python3
"""PSR Cost Tracker — Azure spend + per-run estimates from POC data."""

import json, subprocess, sys, os
from datetime import datetime, timedelta

SUBSCRIPTION_ID = "80b31d19-b663-4936-b8ee-93f7af5b1d27"
BUDGET_NAME = "psr-monthly-budget"

# Per-run cost model (from research.md pricing)
PRICING = {
    "speech_fast_per_hour": 1.00,
    "speech_batch_per_hour": 0.36,
    "o4_mini_in_per_1m": 1.10,
    "o4_mini_out_per_1m": 4.40,
    "gpt41_in_per_1m": 2.00,
    "gpt41_out_per_1m": 8.00,
    "gpt41_mini_in_per_1m": 0.40,
    "gpt41_mini_out_per_1m": 1.60,
    "gpt41_nano_in_per_1m": 0.10,  # estimate
    "gpt41_nano_out_per_1m": 0.40,  # estimate
}

FREE_SPEECH_HOURS = 5.0  # per month


def az(cmd):
    """Run az CLI command, return parsed JSON or None."""
    try:
        r = subprocess.run(f"az {cmd}", shell=True, capture_output=True, text=True, timeout=30)
        return json.loads(r.stdout) if r.returncode == 0 and r.stdout.strip() else None
    except Exception:
        return None


def get_azure_costs():
    """Query Azure Cost Management API for actual costs."""
    print("=" * 60)
    print("AZURE COST MANAGEMENT")
    print("=" * 60)

    # Budget status
    budget = az(f"consumption budget show --budget-name {BUDGET_NAME} -o json 2>/dev/null")
    if budget:
        spent = float(budget.get("currentSpend", {}).get("amount", 0))
        limit = float(budget.get("amount", 100))
        print(f"\nBudget: ${limit:.0f}/mo | Spent: ${spent:.2f} | Remaining: ${limit - spent:.2f}")
    else:
        print("\nBudget: could not query (run 'az login' if expired)")

    # Cost breakdown by service (current month)
    body = json.dumps({
        "type": "ActualCost",
        "timeframe": "MonthToDate",
        "dataset": {
            "granularity": "None",
            "aggregation": {"totalCost": {"name": "Cost", "function": "Sum"}},
            "grouping": [{"type": "Dimension", "name": "ServiceName"}]
        }
    })
    url = f"https://management.azure.com/subscriptions/{SUBSCRIPTION_ID}/providers/Microsoft.CostManagement/query?api-version=2023-11-01"
    result = az(f"rest --method post --url \"{url}\" --body '{body}' 2>/dev/null")

    rows = result.get("properties", {}).get("rows", []) if result else []
    if rows:
        print(f"\nCosts this month (by service):")
        total = 0
        for row in rows:
            cost, service, currency = row[0], row[1], row[2]
            if cost > 0:
                print(f"  {service:<40} ${cost:.4f}")
                total += cost
        print(f"  {'TOTAL':<40} ${total:.4f}")
    else:
        print("\nNo Azure costs posted yet (data lags 24-72 hrs, or all usage within free tier)")


def estimate_per_run():
    """Calculate per-run cost estimates from POC result files."""
    print("\n" + "=" * 60)
    print("PER-RUN COST ESTIMATES (from POC data)")
    print("=" * 60)

    poc_dir = os.path.dirname(os.path.abspath(__file__))
    runs = []

    # POC #5 — Azure basic (single GPT-4o call)
    r = _load(os.path.join(poc_dir, "azure_poc_result.json"))
    if r:
        runs.append({
            "name": "POC #5 Basic (GPT-4o single pass)",
            "speech_hrs": 0,  # used clip, negligible
            "openai_est": 0.01,
            "total": 0.01,
        })

    # POC #5 — Multipass
    r = _load(os.path.join(poc_dir, "multipass_result_piper_called_according_to_his_purpose.json"))
    if r:
        dur_hrs = r.get("transcript_duration", 0) / 3600
        runs.append({
            "name": "POC #5 Multipass (o4-mini + GPT-4.1 + GPT-4.1-mini)",
            "speech_hrs": dur_hrs,
            "speech_cost": dur_hrs * PRICING["speech_fast_per_hour"],
            "openai_est": 0.09,  # from research.md actual measurement
            "total": dur_hrs * PRICING["speech_fast_per_hour"] + 0.09,
            "duration_min": r.get("transcript_duration", 0) / 60,
            "words": r.get("transcript_words", 0),
        })

    # POC #6 — Fast transcription
    r = _load(os.path.join(poc_dir, "fast_transcription_result_piper_called_according_to_his_purpose.json"))
    if r:
        dur_hrs = r.get("duration_milliseconds", 0) / 3600000
        runs.append({
            "name": "POC #6 Fast Transcription (speech only)",
            "speech_hrs": dur_hrs,
            "speech_cost": dur_hrs * PRICING["speech_fast_per_hour"],
            "openai_est": 0,
            "total": dur_hrs * PRICING["speech_fast_per_hour"],
            "duration_min": r.get("duration_minutes", 0),
            "words": r.get("word_count", 0),
        })

    total_speech_hrs = 0
    total_cost = 0

    for run in runs:
        print(f"\n  {run['name']}")
        if run.get("duration_min"):
            print(f"    Audio: {run['duration_min']:.1f} min | Words: {run.get('words', '?')}")
        if run.get("speech_cost"):
            print(f"    Speech: ${run['speech_cost']:.4f} ({run['speech_hrs']:.3f} hrs)")
        print(f"    OpenAI: ${run['openai_est']:.4f}")
        print(f"    Run total: ${run['total']:.4f}")
        total_speech_hrs += run.get("speech_hrs", 0)
        total_cost += run["total"]

    print(f"\n  {'─' * 50}")
    print(f"  Total speech hours used: {total_speech_hrs:.3f} / {FREE_SPEECH_HOURS:.0f} free")
    free_remaining = max(0, FREE_SPEECH_HOURS - total_speech_hrs)
    print(f"  Free speech hours remaining: {free_remaining:.3f}")
    actual_speech_cost = max(0, (total_speech_hrs - FREE_SPEECH_HOURS)) * PRICING["speech_fast_per_hour"]
    print(f"  Speech cost (after free tier): ${actual_speech_cost:.4f}")
    print(f"  OpenAI cost: ${sum(r['openai_est'] for r in runs):.4f}")
    print(f"  TOTAL ACTUAL COST: ${actual_speech_cost + sum(r['openai_est'] for r in runs):.4f}")


def production_projections():
    """Show what production runs would cost."""
    print("\n" + "=" * 60)
    print("PRODUCTION COST PROJECTIONS (per sermon)")
    print("=" * 60)

    for dur_min in [30, 40, 60]:
        dur_hrs = dur_min / 60
        speech = dur_hrs * PRICING["speech_fast_per_hour"]
        # Estimate tokens: ~175 words/min * dur_min = words, ~1.3 tokens/word
        words = 175 * dur_min
        tokens = words * 1.3
        p1 = (tokens / 1e6) * PRICING["o4_mini_in_per_1m"] + (3000 / 1e6) * PRICING["o4_mini_out_per_1m"]
        p2 = (tokens / 1e6) * PRICING["gpt41_in_per_1m"] + (3000 / 1e6) * PRICING["gpt41_out_per_1m"]
        p3 = (tokens / 1e6) * PRICING["gpt41_mini_in_per_1m"] + (2000 / 1e6) * PRICING["gpt41_mini_out_per_1m"]
        classify = (tokens / 1e6) * PRICING["gpt41_nano_in_per_1m"] + (1000 / 1e6) * PRICING["gpt41_nano_out_per_1m"]
        openai_total = p1 + p2 + p3 + classify
        total = speech + openai_total

        print(f"\n  {dur_min}-min sermon (~{words:,} words)")
        print(f"    Speech (fast):  ${speech:.3f}")
        print(f"    Pass 1 (o4-mini):     ${p1:.4f}")
        print(f"    Pass 2 (GPT-4.1):     ${p2:.4f}")
        print(f"    Pass 3 (GPT-4.1-mini):${p3:.4f}")
        print(f"    Classify (nano):      ${classify:.4f}")
        print(f"    OpenAI subtotal:      ${openai_total:.4f}")
        print(f"    TOTAL:                ${total:.3f}")


def _load(path):
    try:
        with open(path) as f:
            return json.load(f)
    except Exception:
        return None


if __name__ == "__main__":
    get_azure_costs()
    estimate_per_run()
    production_projections()
