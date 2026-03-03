"""Tests for schema.py — pure logic, no mocks needed."""
import datetime
from unittest.mock import patch

import pytest
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from schema import (
    CATEGORY_WEIGHTS,
    CATEGORY_KEY_MAP,
    NORM_ADJUSTMENTS,
    new_sermon_doc,
    compute_composite,
    normalize_scores,
    build_summary_prompt,
    fail_sermon_doc,
)


# ── Fixtures ──

def _raw_scores(score=80):
    """Build raw_scores dict matching LLM pass output format."""
    return {k: {"score": score, "reasoning": f"{k} reasoning"} for k in CATEGORY_WEIGHTS}


# ── Constants ──

class TestConstants:
    def test_weights_sum_to_100(self):
        assert sum(CATEGORY_WEIGHTS.values()) == 100

    def test_weights_has_8_categories(self):
        assert len(CATEGORY_WEIGHTS) == 8

    def test_key_map_covers_all_categories(self):
        assert set(CATEGORY_KEY_MAP.values()) == set(CATEGORY_WEIGHTS.keys())

    def test_norm_adjustments_keys(self):
        assert set(NORM_ADJUSTMENTS.keys()) == {"expository", "topical", "survey"}

    def test_expository_has_no_adjustments(self):
        assert NORM_ADJUSTMENTS["expository"] == {}

    def test_topical_adjustments(self):
        adj = NORM_ADJUSTMENTS["topical"]
        assert adj == {"biblicalAccuracy": 5, "timeInTheWord": 8, "passageFocus": 10}

    def test_survey_adjustments(self):
        adj = NORM_ADJUSTMENTS["survey"]
        assert adj == {"biblicalAccuracy": 3, "timeInTheWord": 5, "passageFocus": 12}


# ── new_sermon_doc ──

class TestNewSermonDoc:
    def test_basic_fields(self):
        doc = new_sermon_doc("id-1", "sermon.mp3")
        assert doc["id"] == "id-1"
        assert doc["filename"] == "sermon.mp3"
        assert doc["status"] == "processing"
        assert doc["title"] == "sermon.mp3"  # falls back to filename
        assert doc["pastor"] is None

    def test_with_title_and_pastor(self):
        doc = new_sermon_doc("id-2", "f.mp3", title="Grace", pastor="John")
        assert doc["title"] == "Grace"
        assert doc["pastor"] == "John"

    def test_date_is_today(self):
        doc = new_sermon_doc("id-3", "f.mp3")
        assert doc["date"] == datetime.datetime.utcnow().strftime("%Y-%m-%d")

    def test_null_fields(self):
        doc = new_sermon_doc("id-4", "f.mp3")
        for field in ["duration", "sermonType", "compositePsr", "summary",
                       "categories", "strengths", "improvements", "transcript",
                       "classificationConfidence", "normalizationApplied",
                       "audioMetrics", "error", "failedAt", "blobUrl"]:
            assert doc[field] is None, f"{field} should be None"

    def test_wpm_flag_default(self):
        doc = new_sermon_doc("id-5", "f.mp3")
        assert doc["wpmFlag"] is False

    def test_title_falls_back_to_filename_when_empty_string(self):
        doc = new_sermon_doc("id-6", "f.mp3", title="")
        # empty string is falsy, so falls back
        assert doc["title"] == "f.mp3"


# ── compute_composite ──

class TestComputeComposite:
    def test_all_100(self):
        cats = {k: {"score": 100, "weight": w, "reasoning": ""} for k, w in CATEGORY_WEIGHTS.items()}
        assert compute_composite(cats) == 100.0

    def test_all_0(self):
        cats = {k: {"score": 0, "weight": w, "reasoning": ""} for k, w in CATEGORY_WEIGHTS.items()}
        assert compute_composite(cats) == 0.0

    def test_all_80(self):
        cats = {k: {"score": 80, "weight": w, "reasoning": ""} for k, w in CATEGORY_WEIGHTS.items()}
        assert compute_composite(cats) == 80.0

    def test_weighted_calculation(self):
        # biblicalAccuracy=100 (25%), everything else=0
        cats = {k: {"score": 0, "weight": w, "reasoning": ""} for k, w in CATEGORY_WEIGHTS.items()}
        cats["biblicalAccuracy"]["score"] = 100
        assert compute_composite(cats) == 25.0

    def test_piper_baseline_range(self):
        # Piper benchmark: ~87-88 composite
        cats = {
            "biblicalAccuracy": {"score": 95, "weight": 25, "reasoning": ""},
            "timeInTheWord": {"score": 85, "weight": 20, "reasoning": ""},
            "passageFocus": {"score": 90, "weight": 10, "reasoning": ""},
            "clarity": {"score": 82, "weight": 10, "reasoning": ""},
            "engagement": {"score": 89, "weight": 10, "reasoning": ""},
            "application": {"score": 78, "weight": 10, "reasoning": ""},
            "delivery": {"score": 85, "weight": 10, "reasoning": ""},
            "emotionalRange": {"score": 80, "weight": 5, "reasoning": ""},
        }
        composite = compute_composite(cats)
        assert 85 < composite < 92


# ── normalize_scores ──

class TestNormalizeScores:
    def test_expository_no_change(self):
        raw = _raw_scores(80)
        cats, applied = normalize_scores(raw, "expository", 95)
        assert applied == "full"
        for k in CATEGORY_WEIGHTS:
            assert cats[k]["score"] == 80

    def test_topical_full_normalization(self):
        raw = _raw_scores(80)
        cats, applied = normalize_scores(raw, "topical", 95)
        assert applied == "full"
        assert cats["biblicalAccuracy"]["score"] == 85  # +5
        assert cats["timeInTheWord"]["score"] == 88     # +8
        assert cats["passageFocus"]["score"] == 90      # +10
        assert cats["clarity"]["score"] == 80           # no adj

    def test_topical_half_normalization(self):
        raw = _raw_scores(80)
        cats, applied = normalize_scores(raw, "topical", 85)
        assert applied == "half"
        assert cats["biblicalAccuracy"]["score"] == 82  # +2.5 rounded
        assert cats["timeInTheWord"]["score"] == 84     # +4
        assert cats["passageFocus"]["score"] == 85      # +5

    def test_low_confidence_no_normalization(self):
        raw = _raw_scores(80)
        cats, applied = normalize_scores(raw, "topical", 75)
        assert applied == "none"
        for k in CATEGORY_WEIGHTS:
            assert cats[k]["score"] == 80

    def test_score_capped_at_100(self):
        raw = _raw_scores(98)
        cats, _ = normalize_scores(raw, "topical", 95)
        assert cats["passageFocus"]["score"] == 100  # 98+10 capped

    def test_survey_full_normalization(self):
        raw = _raw_scores(80)
        cats, applied = normalize_scores(raw, "survey", 92)
        assert applied == "full"
        assert cats["biblicalAccuracy"]["score"] == 83  # +3
        assert cats["timeInTheWord"]["score"] == 85     # +5
        assert cats["passageFocus"]["score"] == 92      # +12

    def test_unknown_sermon_type_no_adjustment(self):
        raw = _raw_scores(80)
        cats, applied = normalize_scores(raw, "unknown_type", 95)
        assert applied == "full"
        for k in CATEGORY_WEIGHTS:
            assert cats[k]["score"] == 80

    def test_preserves_weight_and_reasoning(self):
        raw = _raw_scores(80)
        cats, _ = normalize_scores(raw, "expository", 95)
        for k in CATEGORY_WEIGHTS:
            assert cats[k]["weight"] == CATEGORY_WEIGHTS[k]
            assert cats[k]["reasoning"] == f"{k} reasoning"

    def test_confidence_boundary_90(self):
        _, applied = normalize_scores(_raw_scores(80), "topical", 90)
        assert applied == "full"

    def test_confidence_boundary_80(self):
        _, applied = normalize_scores(_raw_scores(80), "topical", 80)
        assert applied == "half"

    def test_confidence_boundary_79(self):
        _, applied = normalize_scores(_raw_scores(80), "topical", 79)
        assert applied == "none"


# ── build_summary_prompt ──

class TestBuildSummaryPrompt:
    def test_contains_all_categories(self):
        cats = {k: {"score": 80, "weight": w, "reasoning": ""} for k, w in CATEGORY_WEIGHTS.items()}
        prompt = build_summary_prompt(cats, "expository")
        for k in CATEGORY_WEIGHTS:
            assert k in prompt

    def test_contains_sermon_type(self):
        cats = {k: {"score": 80, "weight": w, "reasoning": ""} for k, w in CATEGORY_WEIGHTS.items()}
        prompt = build_summary_prompt(cats, "topical")
        assert "topical" in prompt

    def test_contains_scores(self):
        cats = {k: {"score": 95, "weight": w, "reasoning": ""} for k, w in CATEGORY_WEIGHTS.items()}
        prompt = build_summary_prompt(cats, "expository")
        assert "95/100" in prompt


# ── fail_sermon_doc ──

class TestFailSermonDoc:
    def test_status_is_failed(self):
        doc = fail_sermon_doc("something broke")
        assert doc["status"] == "failed"

    def test_error_message(self):
        doc = fail_sermon_doc("timeout")
        assert doc["error"] == "timeout"

    def test_failed_at_is_iso(self):
        doc = fail_sermon_doc("err")
        assert doc["failedAt"].endswith("Z")
        # Should be parseable
        datetime.datetime.fromisoformat(doc["failedAt"].rstrip("Z"))
