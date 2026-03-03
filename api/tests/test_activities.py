"""Tests for activities.py — all external services mocked."""
import json
import os
import sys
from unittest.mock import patch, MagicMock

import numpy as np
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

os.environ.update({
    "OPENAI_KEY": "test-key",
    "OPENAI_API_VERSION": "2025-01-01-preview",
    "OPENAI_ENDPOINT": "https://test.openai.azure.com",
    "SPEECH_KEY": "test-speech-key",
    "SPEECH_ENDPOINT": "https://eastus2.api.cognitive.microsoft.com",
    "COSMOS_CONNECTION_STRING": "AccountEndpoint=https://test.documents.azure.com:443/;AccountKey=dGVzdA==;",
    "STORAGE_CONNECTION_STRING": "DefaultEndpointsProtocol=https;AccountName=test;AccountKey=dGVzdA==;EndpointSuffix=core.windows.net",
})

import activities


# ── Helpers ──

def _mock_openai_response(content: dict):
    mock_resp = MagicMock()
    mock_resp.choices = [MagicMock()]
    mock_resp.choices[0].message.content = json.dumps(content)
    return mock_resp


def _mock_openai_client(response_content: dict):
    client = MagicMock()
    client.chat.completions.create.return_value = _mock_openai_response(response_content)
    return client


# ── transcribe ──

class TestTranscribe:
    def _run(self, text, duration_ms, phrases=None):
        mock_blob = MagicMock()
        mock_blob.download_blob.return_value.readall.return_value = b"audio"

        mock_tc = MagicMock()
        result = MagicMock()
        if text:
            combined = MagicMock()
            combined.text = text
            result.combined_phrases = [combined]
        else:
            result.combined_phrases = []
        result.duration_milliseconds = duration_ms
        result.phrases = phrases or []
        mock_tc.transcribe.return_value = result

        from azure.storage.blob import BlobClient
        from azure.ai.transcription import TranscriptionClient

        with patch.object(BlobClient, "from_connection_string", return_value=mock_blob), \
             patch("azure.ai.transcription.TranscriptionClient", return_value=mock_tc), \
             patch("azure.ai.transcription.models.TranscriptionContent"), \
             patch("azure.ai.transcription.models.TranscriptionOptions"), \
             patch("azure.core.credentials.AzureKeyCredential"):
            return activities.transcribe({"blobUrl": "test/s.mp3", "sermonId": "id-1"})

    def test_basic(self):
        phrase = MagicMock(text="Romans 8:28 says all things work together",
                           offset_milliseconds=0, duration_milliseconds=5000)
        result = self._run("Romans 8:28 says all things work together", 60000, [phrase])
        assert result["fullText"] == "Romans 8:28 says all things work together"
        assert result["wordCount"] == 7
        assert result["durationMs"] == 60000
        assert result["wpm"] == 7.0
        assert len(result["segments"]) == 1
        assert result["segments"][0]["type"] == "teaching"
        assert result["segments"][0]["start"] == 0.0
        assert result["segments"][0]["end"] == 5.0

    def test_empty_result(self):
        result = self._run("", 0)
        assert result["fullText"] == ""
        assert result["wordCount"] == 0
        assert result["wpm"] == 0
        assert result["segments"] == []

    def test_zero_duration(self):
        result = self._run("hello world", 0)
        assert result["wpm"] == 0

    def test_multiple_phrases(self):
        p1 = MagicMock(text="First phrase", offset_milliseconds=0, duration_milliseconds=3000)
        p2 = MagicMock(text="Second phrase", offset_milliseconds=3000, duration_milliseconds=4000)
        result = self._run("First phrase Second phrase", 7000, [p1, p2])
        assert len(result["segments"]) == 2
        assert result["segments"][1]["start"] == 3.0
        assert result["segments"][1]["end"] == 7.0


# ── analyze_audio ──

class TestAnalyzeAudio:
    def _run(self, pitch_freqs, intensity_vals, duration=120.0):
        mock_blob = MagicMock()
        mock_blob.download_blob.return_value.readall.return_value = b"fake"

        mock_snd = MagicMock()
        mock_snd.duration = duration
        mock_pitch = MagicMock()
        mock_pitch.selected_array = {"frequency": np.array(pitch_freqs)}
        mock_intensity = MagicMock()
        mock_intensity.values = np.array([intensity_vals])
        mock_snd.to_pitch.return_value = mock_pitch
        mock_snd.to_intensity.return_value = mock_intensity

        with patch("activities._blob_client", return_value=mock_blob), \
             patch("activities.tempfile") as mock_tmp, \
             patch("activities.os") as mock_os, \
             patch("parselmouth.Sound", return_value=mock_snd):
            f = MagicMock()
            f.name = "/tmp/fake.mp3"
            mock_tmp.NamedTemporaryFile.return_value.__enter__ = lambda s: f
            mock_tmp.NamedTemporaryFile.return_value.__exit__ = lambda s, *a: None
            mock_os.unlink = MagicMock()
            return activities.analyze_audio({"blobUrl": "test/s.mp3"})

    def test_normal_audio(self):
        result = self._run(
            [100.0, 150.0, 0.0, 200.0, 120.0],
            [30.0, 50.0, 60.0, 55.0, 45.0, 10.0, 65.0, 58.0, 52.0, 48.0],
        )
        assert result["pitchMeanHz"] > 0
        assert result["pitchRangeHz"] == 100.0  # 200 - 100
        assert result["durationSeconds"] == 120.0
        assert "noiseFloorDb" in result
        assert "pauseCount" in result
        assert "pausesPerMinute" in result

    def test_no_voiced_frames(self):
        result = self._run([0.0, 0.0, 0.0], [30.0, 30.0, 30.0])
        assert result["pitchMeanHz"] == 0
        assert result["pitchStdHz"] == 0
        assert result["pitchRangeHz"] == 0

    def test_zero_duration(self):
        result = self._run([100.0], [50.0, 50.0], duration=0.0)
        assert result["pausesPerMinute"] == 0


# ── LLM Passes ──

class TestPass1Biblical:
    @patch("activities._openai_client")
    def test_returns_3_categories(self, mock_fn):
        mock_fn.return_value = _mock_openai_client({
            "biblical_accuracy": {"score": 90, "reasoning": "Strong"},
            "time_in_the_word": {"score": 85, "reasoning": "Dense"},
            "passage_focus": {"score": 88, "reasoning": "Focused"},
        })
        result = activities.pass1_biblical({"transcript": "Test"})
        assert set(result.keys()) == {"biblicalAccuracy", "timeInTheWord", "passageFocus"}
        assert result["biblicalAccuracy"]["score"] == 90
        assert result["biblicalAccuracy"]["reasoning"] == "Strong"


class TestPass2Structure:
    @patch("activities._openai_client")
    def test_returns_3_categories(self, mock_fn):
        mock_fn.return_value = _mock_openai_client({
            "clarity": {"score": 82, "reasoning": "Clear"},
            "application": {"score": 75, "reasoning": "Some"},
            "engagement": {"score": 88, "reasoning": "Dynamic"},
        })
        result = activities.pass2_structure({"transcript": "Test"})
        assert set(result.keys()) == {"clarity", "application", "engagement"}
        assert result["clarity"]["score"] == 82


class TestPass3Delivery:
    @patch("activities._openai_client")
    def test_returns_2_categories(self, mock_fn):
        mock_fn.return_value = _mock_openai_client({
            "delivery": {"score": 78, "reasoning": "Good"},
            "emotional_range": {"score": 72, "reasoning": "Varied"},
        })
        audio = {
            "pitchMeanHz": 150, "pitchStdHz": 35, "pitchRangeHz": 200,
            "intensityMeanDb": 65, "intensityRangeDb": 30, "noiseFloorDb": 20,
            "pauseCount": 50, "pausesPerMinute": 12, "durationSeconds": 250,
        }
        result = activities.pass3_delivery({"transcript": "Test", "audioMetrics": audio, "wpm": 145})
        assert set(result.keys()) == {"delivery", "emotionalRange"}
        assert result["emotionalRange"]["score"] == 72


# ── classify_sermon ──

class TestClassifySermon:
    @patch("activities._openai_client")
    def test_basic(self, mock_fn):
        mock_fn.return_value = _mock_openai_client({
            "sermon_type": "expository", "confidence": 92,
            "title": "Called According", "pastor": "Piper",
            "main_passage": "Romans 8:28-30", "reasoning": "Verse by verse",
        })
        result = activities.classify_sermon({
            "transcript": " ".join(["word"] * 1000),
            "userTitle": None, "userPastor": None,
        })
        assert result["sermonType"] == "expository"
        assert result["confidence"] == 92
        assert result["title"] == "Called According"

    @patch("activities._openai_client")
    def test_user_values_override(self, mock_fn):
        mock_fn.return_value = _mock_openai_client({
            "sermon_type": "topical", "confidence": 80,
            "title": "LLM Title", "pastor": "LLM Pastor",
            "main_passage": None, "reasoning": "test",
        })
        result = activities.classify_sermon({
            "transcript": " ".join(["word"] * 1000),
            "userTitle": "My Title", "userPastor": "My Pastor",
        })
        assert result["title"] == "My Title"
        assert result["pastor"] == "My Pastor"

    @patch("activities._openai_client")
    def test_defaults_on_missing_keys(self, mock_fn):
        mock_fn.return_value = _mock_openai_client({})
        result = activities.classify_sermon({
            "transcript": " ".join(["word"] * 100),
            "userTitle": None, "userPastor": None,
        })
        assert result["sermonType"] == "topical"
        assert result["confidence"] == 50
        assert result["title"] == "Untitled"

    @patch("activities._openai_client")
    def test_short_transcript(self, mock_fn):
        mock_fn.return_value = _mock_openai_client({
            "sermon_type": "topical", "confidence": 60,
            "title": "Short", "pastor": None, "main_passage": None, "reasoning": "short",
        })
        result = activities.classify_sermon({
            "transcript": "hello world", "userTitle": None, "userPastor": None,
        })
        assert result["sermonType"] == "topical"


# ── classify_segments ──

class TestClassifySegments:
    @patch("activities._openai_client")
    def test_basic(self, mock_fn):
        mock_fn.return_value = _mock_openai_client({"types": ["scripture", "teaching", "application"]})
        segs = [{"start": i, "end": i + 10, "text": f"seg {i}"} for i in range(3)]
        result = activities.classify_segments({"segments": segs})
        assert len(result) == 3
        assert result[0]["type"] == "scripture"
        assert result[2]["type"] == "application"

    @patch("activities._openai_client")
    def test_invalid_type_defaults(self, mock_fn):
        mock_fn.return_value = _mock_openai_client({"types": ["invalid"]})
        result = activities.classify_segments({"segments": [{"start": 0, "end": 10, "text": "t"}]})
        assert result[0]["type"] == "teaching"

    @patch("activities._openai_client")
    def test_short_response_padded(self, mock_fn):
        mock_fn.return_value = _mock_openai_client({"types": ["scripture"]})
        segs = [{"start": i, "end": i + 1, "text": "t"} for i in range(3)]
        result = activities.classify_segments({"segments": segs})
        assert result[0]["type"] == "scripture"
        assert result[1]["type"] == "teaching"
        assert result[2]["type"] == "teaching"

    @patch("activities._openai_client")
    def test_batching_over_200(self, mock_fn):
        client = MagicMock()
        client.chat.completions.create.side_effect = [
            _mock_openai_response({"types": ["scripture"] * 200}),
            _mock_openai_response({"types": ["application"] * 50}),
        ]
        mock_fn.return_value = client
        segs = [{"start": i, "end": i + 1, "text": f"s{i}"} for i in range(250)]
        result = activities.classify_segments({"segments": segs})
        assert len(result) == 250
        assert client.chat.completions.create.call_count == 2
        assert result[0]["type"] == "scripture"
        assert result[200]["type"] == "application"

    @patch("activities._openai_client")
    def test_empty_types(self, mock_fn):
        mock_fn.return_value = _mock_openai_client({})
        result = activities.classify_segments({"segments": [{"start": 0, "end": 10, "text": "t"}]})
        assert result[0]["type"] == "teaching"

    @patch("activities._openai_client")
    def test_preserves_segment_fields(self, mock_fn):
        mock_fn.return_value = _mock_openai_client({"types": ["prayer"]})
        result = activities.classify_segments({"segments": [{"start": 1.5, "end": 3.2, "text": "Lord"}]})
        assert result[0]["start"] == 1.5
        assert result[0]["end"] == 3.2
        assert result[0]["text"] == "Lord"


# ── generate_summary ──

class TestGenerateSummary:
    @patch("activities._openai_client")
    def test_basic(self, mock_fn):
        mock_fn.return_value = _mock_openai_client({
            "summary": "Strong sermon.", "strengths": ["a", "b", "c"], "improvements": ["x", "y"],
        })
        from schema import CATEGORY_WEIGHTS
        cats = {k: {"score": 80, "weight": w, "reasoning": ""} for k, w in CATEGORY_WEIGHTS.items()}
        result = activities.generate_summary({"categories": cats, "sermonType": "expository"})
        assert result["summary"] == "Strong sermon."
        assert len(result["strengths"]) == 3


# ── update_sermon ──

class TestUpdateSermon:
    @patch("activities._cosmos_client")
    def test_basic(self, mock_fn):
        container = MagicMock()
        container.read_item.return_value = {"id": "s1", "status": "processing"}
        mock_fn.return_value = container
        result = activities.update_sermon({"sermonId": "s1", "updates": {"status": "complete", "compositePsr": 85.0}})
        assert result == {"ok": True}
        container.read_item.assert_called_once_with("s1", partition_key="s1")
        upserted = container.upsert_item.call_args[0][0]
        assert upserted["status"] == "complete"
        assert upserted["compositePsr"] == 85.0


# ── Shared helpers ──

class TestSharedHelpers:
    def test_openai_client(self):
        with patch("activities.AzureOpenAI") as mock_cls:
            activities._openai_client()
            mock_cls.assert_called_once()
            assert mock_cls.call_args[1]["api_key"] == "test-key"

    def test_cosmos_client(self):
        with patch("activities.CosmosClient", create=True) as mock_cls:
            # _cosmos_client does a lazy import, so we need to patch at the module level
            from azure.cosmos import CosmosClient
            with patch.object(CosmosClient, "from_connection_string") as mock_cs:
                mock_db = MagicMock()
                mock_cs.return_value.get_database_client.return_value = mock_db
                activities._cosmos_client()
                mock_cs.assert_called_once()

    def test_blob_client(self):
        from azure.storage.blob import BlobClient
        with patch.object(BlobClient, "from_connection_string") as mock_bc:
            activities._blob_client("test/sermon.mp3")
            mock_bc.assert_called_once_with(
                os.environ["STORAGE_CONNECTION_STRING"], "sermon-audio", "test/sermon.mp3"
            )
