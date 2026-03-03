"""Tests for function_app.py — HTTP triggers, helpers, constants."""
import json
import os
import sys
from unittest.mock import patch, MagicMock, AsyncMock

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

from function_app import (
    ALLOWED_TYPES,
    MAX_SIZE,
    _json_response,
    _default_audio_metrics,
)
import azure.functions as func


# ── Constants ──

class TestConstants:
    def test_allowed_types_mp3(self):
        assert ALLOWED_TYPES["audio/mpeg"] == ".mp3"

    def test_allowed_types_wav(self):
        assert ALLOWED_TYPES["audio/wav"] == ".wav"
        assert ALLOWED_TYPES["audio/x-wav"] == ".wav"
        assert ALLOWED_TYPES["audio/wave"] == ".wav"

    def test_allowed_types_m4a(self):
        assert ALLOWED_TYPES["audio/mp4"] == ".m4a"
        assert ALLOWED_TYPES["audio/x-m4a"] == ".m4a"

    def test_no_video(self):
        assert "video/mp4" not in ALLOWED_TYPES

    def test_max_size(self):
        assert MAX_SIZE == 100 * 1024 * 1024


# ── _json_response ──

class TestJsonResponse:
    def test_default_200(self):
        resp = _json_response({"ok": True})
        assert resp.status_code == 200
        assert resp.mimetype == "application/json"
        assert json.loads(resp.get_body()) == {"ok": True}

    def test_custom_status(self):
        resp = _json_response({"error": "bad"}, 400)
        assert resp.status_code == 400

    def test_list_body(self):
        resp = _json_response([1, 2, 3])
        assert json.loads(resp.get_body()) == [1, 2, 3]

    def test_empty_dict(self):
        resp = _json_response({})
        assert json.loads(resp.get_body()) == {}


# ── _default_audio_metrics ──

class TestDefaultAudioMetrics:
    def test_all_zeros(self):
        m = _default_audio_metrics()
        assert all(v == 0 for v in m.values())

    def test_has_all_keys(self):
        m = _default_audio_metrics()
        expected = {"pitchMeanHz", "pitchStdHz", "pitchRangeHz",
                    "intensityMeanDb", "intensityRangeDb", "noiseFloorDb",
                    "pauseCount", "pausesPerMinute", "durationSeconds"}
        assert set(m.keys()) == expected

    def test_9_keys(self):
        assert len(_default_audio_metrics()) == 9


# ── Upload validation logic (tested via direct function call, bypassing decorator) ──
# The decorated upload_sermon is wrapped by durable_client_input which expects kwargs.
# We test the core validation logic by importing and calling the inner function directly.

DF_STARTER = json.dumps({
    "taskHubName": "TestHub",
    "creationUrls": {"createNewInstancePostUri": "http://localhost/api/orchestrators/{functionName}"},
    "managementUrls": {
        "id": "INSTANCEID",
        "statusQueryGetUri": "http://localhost/api/instances/INSTANCEID",
        "sendEventPostUri": "http://localhost/api/instances/INSTANCEID/raiseEvent/{eventName}",
        "terminatePostUri": "http://localhost/api/instances/INSTANCEID/terminate",
        "rewindPostUri": "http://localhost/api/instances/INSTANCEID/rewind",
        "purgeHistoryDeleteUri": "http://localhost/api/instances/INSTANCEID",
        "restartPostUri": "http://localhost/api/instances/INSTANCEID/restart",
        "suspendPostUri": "http://localhost/api/instances/INSTANCEID/suspend",
        "resumePostUri": "http://localhost/api/instances/INSTANCEID/resume",
    },
})


class TestUploadValidation:
    async def _call_upload(self, req):
        from function_app import upload_sermon
        import azure.durable_functions as df
        with patch.object(df.DurableOrchestrationClient, "start_new", new_callable=AsyncMock, return_value="inst-1"):
            return await upload_sermon(req, starter=DF_STARTER)

    @pytest.mark.asyncio
    async def test_no_file(self):
        req = MagicMock(spec=func.HttpRequest)
        req.files = {}
        resp = await self._call_upload(req)
        assert resp.status_code == 400
        assert "No file uploaded" in resp.get_body().decode()

    @pytest.mark.asyncio
    async def test_unsupported_type(self):
        req = MagicMock(spec=func.HttpRequest)
        mock_file = MagicMock()
        mock_file.content_type = "video/mp4"
        req.files = {"file": mock_file}
        resp = await self._call_upload(req)
        assert resp.status_code == 400
        assert "Unsupported format" in resp.get_body().decode()

    @pytest.mark.asyncio
    async def test_empty_content_type(self):
        req = MagicMock(spec=func.HttpRequest)
        mock_file = MagicMock()
        mock_file.content_type = None
        req.files = {"file": mock_file}
        resp = await self._call_upload(req)
        assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test_file_too_large(self):
        req = MagicMock(spec=func.HttpRequest)
        mock_file = MagicMock()
        mock_file.content_type = "audio/mpeg"
        mock_file.read.return_value = b"x" * (MAX_SIZE + 1)
        req.files = {"file": mock_file}
        resp = await self._call_upload(req)
        assert resp.status_code == 400
        assert "too large" in resp.get_body().decode()

    @pytest.mark.asyncio
    async def test_successful_upload(self):
        req = MagicMock(spec=func.HttpRequest)
        mock_file = MagicMock()
        mock_file.content_type = "audio/mpeg"
        mock_file.read.return_value = b"fake audio"
        mock_file.filename = "sermon.mp3"
        req.files = {"file": mock_file}
        req.form = {"title": "Test", "pastor": "Pastor"}

        mock_blob = MagicMock()
        mock_container = MagicMock()
        mock_cosmos = MagicMock()
        mock_cosmos.get_database_client.return_value.get_container_client.return_value = mock_container

        from azure.storage.blob import BlobClient
        from azure.cosmos import CosmosClient
        import azure.durable_functions as df

        mock_client = AsyncMock()
        mock_client.start_new = AsyncMock(return_value="inst-1")

        with patch.object(BlobClient, "from_connection_string", return_value=mock_blob), \
             patch.object(CosmosClient, "from_connection_string", return_value=mock_cosmos), \
             patch.object(df, "DurableOrchestrationClient", return_value=mock_client):
            resp = await self._call_upload(req)

        assert resp.status_code == 202
        body = json.loads(resp.get_body())
        assert "id" in body
        assert body["status"] == "processing"
        mock_blob.upload_blob.assert_called_once()
        mock_container.create_item.assert_called_once()

    @pytest.mark.asyncio
    async def test_upload_no_filename(self):
        req = MagicMock(spec=func.HttpRequest)
        mock_file = MagicMock()
        mock_file.content_type = "audio/mpeg"
        mock_file.read.return_value = b"data"
        mock_file.filename = None
        req.files = {"file": mock_file}
        req.form = {}

        from azure.storage.blob import BlobClient
        from azure.cosmos import CosmosClient
        import azure.durable_functions as df

        mock_client = AsyncMock()
        mock_client.start_new = AsyncMock(return_value="inst-1")

        with patch.object(BlobClient, "from_connection_string", return_value=MagicMock()), \
             patch.object(CosmosClient, "from_connection_string", return_value=MagicMock(
                 get_database_client=MagicMock(return_value=MagicMock(
                     get_container_client=MagicMock(return_value=MagicMock()))))), \
             patch.object(df, "DurableOrchestrationClient", return_value=mock_client):
            resp = await self._call_upload(req)

        assert resp.status_code == 202


# ── list_sermons ──

class TestListSermons:
    @pytest.mark.asyncio
    async def test_returns_items(self):
        from function_app import list_sermons
        from azure.cosmos import CosmosClient

        req = MagicMock(spec=func.HttpRequest)
        mock_container = MagicMock()
        mock_container.query_items.return_value = [
            {"id": "1", "title": "S1", "compositePsr": 85},
            {"id": "2", "title": "S2", "compositePsr": 78},
        ]
        mock_cosmos = MagicMock()
        mock_cosmos.get_database_client.return_value.get_container_client.return_value = mock_container

        with patch.object(CosmosClient, "from_connection_string", return_value=mock_cosmos):
            resp = await list_sermons(req)

        assert resp.status_code == 200
        body = json.loads(resp.get_body())
        assert len(body) == 2

    @pytest.mark.asyncio
    async def test_empty_list(self):
        from function_app import list_sermons
        from azure.cosmos import CosmosClient

        req = MagicMock(spec=func.HttpRequest)
        mock_container = MagicMock()
        mock_container.query_items.return_value = []
        mock_cosmos = MagicMock()
        mock_cosmos.get_database_client.return_value.get_container_client.return_value = mock_container

        with patch.object(CosmosClient, "from_connection_string", return_value=mock_cosmos):
            resp = await list_sermons(req)

        assert json.loads(resp.get_body()) == []


# ── get_sermon ──

class TestGetSermon:
    @pytest.mark.asyncio
    async def test_found(self):
        from function_app import get_sermon
        from azure.cosmos import CosmosClient

        req = MagicMock(spec=func.HttpRequest)
        req.route_params = {"sermon_id": "abc-123"}
        mock_container = MagicMock()
        mock_container.read_item.return_value = {
            "id": "abc-123", "title": "Test",
            "_rid": "x", "_self": "x", "_etag": "x", "_attachments": "x", "_ts": 123,
        }
        mock_cosmos = MagicMock()
        mock_cosmos.get_database_client.return_value.get_container_client.return_value = mock_container

        with patch.object(CosmosClient, "from_connection_string", return_value=mock_cosmos):
            resp = await get_sermon(req)

        assert resp.status_code == 200
        body = json.loads(resp.get_body())
        assert body["id"] == "abc-123"
        for key in ("_rid", "_self", "_etag", "_attachments", "_ts"):
            assert key not in body

    @pytest.mark.asyncio
    async def test_not_found(self):
        from function_app import get_sermon
        from azure.cosmos import CosmosClient, exceptions

        req = MagicMock(spec=func.HttpRequest)
        req.route_params = {"sermon_id": "nonexistent"}
        mock_container = MagicMock()
        mock_container.read_item.side_effect = exceptions.CosmosResourceNotFoundError()
        mock_cosmos = MagicMock()
        mock_cosmos.get_database_client.return_value.get_container_client.return_value = mock_container

        with patch.object(CosmosClient, "from_connection_string", return_value=mock_cosmos):
            resp = await get_sermon(req)

        assert resp.status_code == 404
        assert "not found" in resp.get_body().decode()
