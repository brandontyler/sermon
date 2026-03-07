"""Cosmos DB document schema for sermon records.

This is the single source of truth for the data contract between:
- Pipeline (writes documents)
- API layer (reads/creates documents)
- Frontend (consumes via API)

Field names use camelCase to match the frontend-spec.md API contract.
"""

# Pipeline version — bump when models or scoring prompts change
PIPELINE_VERSION = "2026-03-06c"  # tighter engagement + emotional range calibration (sermon-3pi)
SCORING_MODELS = {
    "pass1_biblical": "o4-mini",
    "pass2_structure": "gpt-5-mini",
    "pass3_delivery": "gpt-5-nano",
    "classification": "gpt-5-nano",
}

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
    lines = []
    for k, v in categories.items():
        line = f"- {k}: {v['score']}/100"
        if v.get("reasoning"):
            line += f" — {v['reasoning']}"
        lines.append(line)
    return f"""Given these sermon scores and reasoning (type: {sermon_type}):
{chr(10).join(lines)}

Return JSON:
- "summary": one sentence overall assessment referencing specific sermon content (max 30 words)
- "strengths": array of exactly 3 specific observations from this sermon (not generic category names)
- "improvements": array of exactly 2-3 specific, actionable suggestions based on the reasoning above"""


def fail_sermon_doc(error_message):
    """Fields to update when pipeline fails."""
    import datetime
    return {
        "status": "failed",
        "error": error_message,
        "failedAt": datetime.datetime.utcnow().isoformat() + "Z",
    }


# ─────────────────────────────────────────────
#  LLM Response Validation (sermon-4e5)
# ─────────────────────────────────────────────

import json as _json
import re as _re


class LLMValidationError(Exception):
    """Raised when LLM response fails schema validation."""
    def __init__(self, message, raw_response=None):
        super().__init__(message)
        self.raw_response = raw_response


def _strip_markdown_fences(text):
    """Remove ```json ... ``` wrapping if present."""
    stripped = text.strip()
    if stripped.startswith("```"):
        stripped = _re.sub(r"^```(?:json)?\s*\n?", "", stripped)
        stripped = _re.sub(r"\n?```\s*$", "", stripped)
    return stripped


def _clamp_score(value):
    """Coerce to int and clamp 0-100. Raises LLMValidationError if not numeric."""
    try:
        n = int(float(value))
    except (TypeError, ValueError):
        raise LLMValidationError(f"Score is not numeric: {value!r}")
    return min(100, max(0, n))


def validate_llm_response(raw_text, required_sections):
    """Parse and validate an LLM JSON response.

    Args:
        raw_text: raw string from LLM (may have markdown fences)
        required_sections: dict mapping snake_case section name to list of required keys.
            Keys named "score" are clamped to 0-100.
            Keys named "reasoning" default to "" if missing.
            Example: {"biblical_accuracy": ["score", "reasoning"], "time_in_the_word": ["score", "reasoning"]}

    Returns:
        Parsed dict with scores clamped and reasoning defaulted.

    Raises:
        LLMValidationError on parse failure or missing required sections.
    """
    cleaned = _strip_markdown_fences(raw_text)
    try:
        data = _json.loads(cleaned)
    except _json.JSONDecodeError as e:
        raise LLMValidationError(f"Invalid JSON from LLM: {e}", raw_response=raw_text)

    if not isinstance(data, dict):
        raise LLMValidationError(f"Expected JSON object, got {type(data).__name__}", raw_response=raw_text)

    for section, keys in required_sections.items():
        if section not in data:
            raise LLMValidationError(f"Missing required section: '{section}'", raw_response=raw_text)
        if not isinstance(data[section], dict):
            raise LLMValidationError(f"Section '{section}' is not an object", raw_response=raw_text)
        for key in keys:
            if key == "score":
                data[section]["score"] = _clamp_score(data[section].get("score"))
            elif key == "reasoning":
                data[section].setdefault("reasoning", "")
            elif key not in data[section]:
                raise LLMValidationError(f"Missing key '{key}' in section '{section}'", raw_response=raw_text)

    return data


def validate_flat_response(raw_text, defaults):
    """Parse and validate a flat (non-nested) LLM JSON response.

    Args:
        raw_text: raw string from LLM
        defaults: dict of key -> default value. Keys present in defaults are
            filled in if missing. Keys NOT in defaults are left as-is.

    Returns:
        Parsed dict with defaults applied.

    Raises:
        LLMValidationError on parse failure.
    """
    cleaned = _strip_markdown_fences(raw_text)
    try:
        data = _json.loads(cleaned)
    except _json.JSONDecodeError as e:
        raise LLMValidationError(f"Invalid JSON from LLM: {e}", raw_response=raw_text)

    if not isinstance(data, dict):
        raise LLMValidationError(f"Expected JSON object, got {type(data).__name__}", raw_response=raw_text)

    for key, default in defaults.items():
        data.setdefault(key, default)

    return data
