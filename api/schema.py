"""Cosmos DB document schema for sermon records.

This is the single source of truth for the data contract between:
- Pipeline (writes documents)
- API layer (reads/creates documents)
- Frontend (consumes via API)

Field names use camelCase to match the frontend-spec.md API contract.
"""

CATEGORY_WEIGHTS = {
    "biblicalAccuracy": 25,
    "timeInTheWord": 20,
    "passageFocus": 10,
    "clarity": 10,
    "engagement": 10,
    "application": 10,
    "delivery": 10,
    "emotionalRange": 5,
}

# Maps POC snake_case keys to camelCase document keys
CATEGORY_KEY_MAP = {
    "biblical_accuracy": "biblicalAccuracy",
    "time_in_the_word": "timeInTheWord",
    "passage_focus": "passageFocus",
    "clarity": "clarity",
    "application": "application",
    "engagement": "engagement",
    "delivery": "delivery",
    "emotional_range": "emotionalRange",
}

# Normalization adjustments by sermon type (POC #7/#10)
NORM_ADJUSTMENTS = {
    "expository": {},
    "topical": {"biblicalAccuracy": 5, "timeInTheWord": 8, "passageFocus": 10},
    "survey": {"biblicalAccuracy": 3, "timeInTheWord": 5, "passageFocus": 12},
}


def new_sermon_doc(sermon_id, filename, title=None, pastor=None):
    """Create initial Cosmos document when upload starts."""
    import datetime
    return {
        "id": sermon_id,
        "status": "processing",
        "title": title or filename,
        "pastor": pastor,
        "date": datetime.datetime.utcnow().strftime("%Y-%m-%d"),
        "duration": None,
        "sermonType": None,
        "compositePsr": None,
        "summary": None,
        "categories": None,
        "strengths": None,
        "improvements": None,
        "transcript": None,
        "classificationConfidence": None,
        "normalizationApplied": None,
        "audioMetrics": None,
        "wpmFlag": False,
        "error": None,
        "failedAt": None,
        "blobUrl": None,
        "filename": filename,
    }


def compute_composite(categories):
    """Compute weighted composite PSR from category scores."""
    return round(
        sum(
            categories[k]["score"] * CATEGORY_WEIGHTS[k] / 100
            for k in CATEGORY_WEIGHTS
        ),
        1,
    )


def normalize_scores(raw_scores, sermon_type, confidence):
    """Apply sermon-type normalization with tiered confidence (POC #10).

    Returns (categories dict, normalization_applied str).
    """
    # Determine normalization level based on confidence
    if confidence >= 90:
        multiplier = 1.0
        applied = "full"
    elif confidence >= 80:
        multiplier = 0.5
        applied = "half"
    else:
        multiplier = 0.0
        applied = "none"

    adjustments = NORM_ADJUSTMENTS.get(sermon_type, {})
    categories = {}
    for key in CATEGORY_WEIGHTS:
        score = raw_scores[key]["score"]
        adj = adjustments.get(key, 0) * multiplier
        categories[key] = {
            "score": min(100, round(score + adj)),
            "weight": CATEGORY_WEIGHTS[key],
            "reasoning": raw_scores[key]["reasoning"],
        }
    return categories, applied


def build_summary_prompt(categories, sermon_type):
    """Build prompt to generate summary + strengths + improvements."""
    lines = [f"- {k}: {v['score']}/100" for k, v in categories.items()]
    return f"""Given these sermon scores (type: {sermon_type}):
{chr(10).join(lines)}

Return JSON:
- "summary": one sentence overall assessment (max 30 words)
- "strengths": array of exactly 3 short strength phrases
- "improvements": array of exactly 2-3 short improvement phrases"""


def fail_sermon_doc(error_message):
    """Fields to update when pipeline fails."""
    import datetime
    return {
        "status": "failed",
        "error": error_message,
        "failedAt": datetime.datetime.utcnow().isoformat() + "Z",
    }
