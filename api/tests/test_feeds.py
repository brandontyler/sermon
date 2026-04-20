"""Tests for feed preview + poll endpoints."""
import contextlib
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
    "ADMIN_KEY": "test-admin",
})

import azure.functions as func

# feedparser isn't installed in test env — provide a mock module
import types
_mock_feedparser = types.ModuleType("feedparser")
_mock_feedparser.parse = MagicMock()
sys.modules.setdefault("feedparser", _mock_feedparser)

from routes.feeds import _preview_feeds, _poll_all_feeds, preview_feeds, poll_feeds_manual

MOCK_STARTER_JSON = json.dumps({
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


def _mock_feed(feed_id="feed-1", active=True, backfill=0, last_polled=None):
    return {
        "id": feed_id,
        "feedUrl": "https://example.com/feed.xml",
        "title": "Test Feed",
        "active": active,
        "backfillCount": backfill,
        "lastPolledAt": last_polled,
        "lastSeenGuid": None,
        "createdAt": "2026-01-01T00:00:00Z",
    }


def _mock_entry(guid="ep-1", has_audio=True):
    entry = {"id": guid, "title": f"Episode {guid}", "published_parsed": (2026, 3, 1, 0, 0, 0, 0, 0, 0)}
    if has_audio:
        entry["enclosures"] = [{"type": "audio/mpeg", "href": "https://example.com/ep.mp3"}]
    else:
        entry["enclosures"] = []
        entry["links"] = []
    return entry


def _patch_cosmos(feeds, existing_guids=None):
    existing = [{"feedGuid": g} for g in (existing_guids or [])]
    mock_feed_container = MagicMock()
    mock_feed_container.query_items.return_value = feeds
    mock_sermon_container = MagicMock()
    mock_sermon_container.query_items.return_value = existing
    mock_cosmos = MagicMock()
    mock_cosmos.get_database_client.return_value.get_container_client.return_value = mock_sermon_container
    return mock_cosmos, mock_feed_container


def _admin_req(method="GET", body=None):
    req = MagicMock(spec=func.HttpRequest)
    req.headers = {"x-admin-key": "test-admin"}
    req.params = {}
    req.method = method
    req.get_body.return_value = json.dumps(body).encode() if body else b""
    return req


def _feed_patches(mock_cosmos, mock_feed_ctr, parsed=None, parse_side_effect=None):
    """Return stacked context managers for Cosmos + feedparser."""
    from azure.cosmos import CosmosClient
    import feedparser
    patches = [
        patch.object(CosmosClient, "from_connection_string", return_value=mock_cosmos),
        patch("helpers._feeds_container", return_value=mock_feed_ctr),
        patch("routes.feeds._feeds_container", return_value=mock_feed_ctr),
    ]
    if parse_side_effect:
        patches.append(patch.object(feedparser, "parse", side_effect=parse_side_effect))
    elif parsed is not None:
        patches.append(patch.object(feedparser, "parse", return_value=parsed))
    return patches


# ── _preview_feeds ──

class TestPreviewFeeds:
    @pytest.mark.asyncio
    async def test_counts_new_episodes(self):
        mock_cosmos, mock_feed_ctr = _patch_cosmos([_mock_feed()])
        parsed = MagicMock()
        parsed.entries = [_mock_entry("ep-1"), _mock_entry("ep-2")]

        with contextlib.ExitStack() as stack:
            for p in _feed_patches(mock_cosmos, mock_feed_ctr, parsed=parsed):
                stack.enter_context(p)
            results = await _preview_feeds()

        assert len(results) == 1
        assert results[0]["newCount"] == 2

    @pytest.mark.asyncio
    async def test_excludes_known_guids(self):
        mock_cosmos, mock_feed_ctr = _patch_cosmos([_mock_feed()], existing_guids=["ep-1"])
        parsed = MagicMock()
        parsed.entries = [_mock_entry("ep-1"), _mock_entry("ep-2")]

        with contextlib.ExitStack() as stack:
            for p in _feed_patches(mock_cosmos, mock_feed_ctr, parsed=parsed):
                stack.enter_context(p)
            results = await _preview_feeds()

        assert results[0]["newCount"] == 1

    @pytest.mark.asyncio
    async def test_skips_non_audio(self):
        mock_cosmos, mock_feed_ctr = _patch_cosmos([_mock_feed()])
        parsed = MagicMock()
        parsed.entries = [_mock_entry("ep-1", has_audio=False)]

        with contextlib.ExitStack() as stack:
            for p in _feed_patches(mock_cosmos, mock_feed_ctr, parsed=parsed):
                stack.enter_context(p)
            results = await _preview_feeds()

        assert results[0]["newCount"] == 0

    @pytest.mark.asyncio
    async def test_empty_feed(self):
        mock_cosmos, mock_feed_ctr = _patch_cosmos([_mock_feed()])
        parsed = MagicMock()
        parsed.entries = []

        with contextlib.ExitStack() as stack:
            for p in _feed_patches(mock_cosmos, mock_feed_ctr, parsed=parsed):
                stack.enter_context(p)
            results = await _preview_feeds()

        assert results[0]["newCount"] == 0

    @pytest.mark.asyncio
    async def test_feed_parse_error(self):
        mock_cosmos, mock_feed_ctr = _patch_cosmos([_mock_feed()])

        with contextlib.ExitStack() as stack:
            for p in _feed_patches(mock_cosmos, mock_feed_ctr, parse_side_effect=Exception("network error")):
                stack.enter_context(p)
            results = await _preview_feeds()

        assert results[0]["newCount"] == 0
        assert "error" in results[0]


# ── preview_feeds HTTP endpoint ──

class TestPreviewFeedsEndpoint:
    @pytest.mark.asyncio
    async def test_returns_total_and_cost(self):
        mock_cosmos, mock_feed_ctr = _patch_cosmos([_mock_feed()])
        parsed = MagicMock()
        parsed.entries = [_mock_entry("ep-1"), _mock_entry("ep-2"), _mock_entry("ep-3")]

        with contextlib.ExitStack() as stack:
            for p in _feed_patches(mock_cosmos, mock_feed_ctr, parsed=parsed):
                stack.enter_context(p)
            resp = await preview_feeds(_admin_req())

        body = json.loads(resp.get_body())
        assert body["totalNew"] == 3
        assert body["estimatedCost"] == 2.25
        assert len(body["feeds"]) == 1


class TestPollFeedIds:
    @pytest.mark.asyncio
    async def test_filters_by_feed_ids(self):
        feeds = [_mock_feed("feed-1"), _mock_feed("feed-2")]
        mock_cosmos, mock_feed_ctr = _patch_cosmos(feeds)
        parsed = MagicMock()
        parsed.entries = []

        starter = AsyncMock()
        with contextlib.ExitStack() as stack:
            for p in _feed_patches(mock_cosmos, mock_feed_ctr, parsed=parsed):
                stack.enter_context(p)
            results = await _poll_all_feeds(starter, feed_ids=["feed-1"])

        assert len(results) == 1
        assert results[0]["feedId"] == "feed-1"

    @pytest.mark.asyncio
    async def test_no_filter_polls_all(self):
        feeds = [_mock_feed("feed-1"), _mock_feed("feed-2")]
        mock_cosmos, mock_feed_ctr = _patch_cosmos(feeds)
        parsed = MagicMock()
        parsed.entries = []

        starter = AsyncMock()
        with contextlib.ExitStack() as stack:
            for p in _feed_patches(mock_cosmos, mock_feed_ctr, parsed=parsed):
                stack.enter_context(p)
            results = await _poll_all_feeds(starter, feed_ids=None)

        assert len(results) == 2


# ── poll_feeds_manual with feedIds body ──

class TestPollManualEndpoint:
    @pytest.mark.asyncio
    async def test_passes_feed_ids(self):
        import azure.durable_functions as df
        with patch.object(df.DurableOrchestrationClient, "__init__", return_value=None), \
             patch("routes.feeds._poll_all_feeds", new_callable=AsyncMock, return_value=[{"feedId": "f1", "new": 0}]) as mock_poll:
            req = _admin_req("POST", body={"feedIds": ["f1"]})
            resp = await poll_feeds_manual(req, starter=MOCK_STARTER_JSON)

        mock_poll.assert_called_once()
        assert mock_poll.call_args[1]["feed_ids"] == ["f1"]
        body = json.loads(resp.get_body())
        assert body["polled"] == 1

    @pytest.mark.asyncio
    async def test_no_body_polls_all(self):
        import azure.durable_functions as df
        with patch.object(df.DurableOrchestrationClient, "__init__", return_value=None), \
             patch("routes.feeds._poll_all_feeds", new_callable=AsyncMock, return_value=[]) as mock_poll:
            req = _admin_req("POST")
            resp = await poll_feeds_manual(req, starter=MOCK_STARTER_JSON)

        mock_poll.assert_called_once()
        assert mock_poll.call_args[1]["feed_ids"] is None


# ── list_feeds: episodeCount + processingCount (sermon-38g) ──

class TestListFeedsEnrichment:
    @pytest.mark.asyncio
    async def test_returns_episode_and_processing_counts(self):
        from routes.feeds import list_feeds
        from azure.cosmos import CosmosClient

        feed_item = {**_mock_feed(), "_rid": "x", "_self": "x", "_etag": "x", "_attachments": "x", "_ts": 1}
        mock_feed_ctr = MagicMock()
        mock_feed_ctr.query_items.return_value = [feed_item]

        mock_sermon_ctr = MagicMock()
        mock_sermon_ctr.query_items.return_value = [
            {"status": "complete", "cnt": 8},
            {"status": "processing", "cnt": 3},
        ]
        mock_cosmos = MagicMock()
        mock_cosmos.get_database_client.return_value.get_container_client.return_value = mock_sermon_ctr

        with patch("routes.feeds._feeds_container", return_value=mock_feed_ctr), \
             patch.object(CosmosClient, "from_connection_string", return_value=mock_cosmos):
            resp = await list_feeds(_admin_req())

        body = json.loads(resp.get_body())
        assert body[0]["episodeCount"] == 8
        assert body[0]["processingCount"] == 3

    @pytest.mark.asyncio
    async def test_zero_processing_when_none(self):
        from routes.feeds import list_feeds
        from azure.cosmos import CosmosClient

        feed_item = {**_mock_feed(), "_rid": "x", "_self": "x", "_etag": "x", "_attachments": "x", "_ts": 1}
        mock_feed_ctr = MagicMock()
        mock_feed_ctr.query_items.return_value = [feed_item]

        mock_sermon_ctr = MagicMock()
        mock_sermon_ctr.query_items.return_value = [{"status": "complete", "cnt": 5}]
        mock_cosmos = MagicMock()
        mock_cosmos.get_database_client.return_value.get_container_client.return_value = mock_sermon_ctr

        with patch("routes.feeds._feeds_container", return_value=mock_feed_ctr), \
             patch.object(CosmosClient, "from_connection_string", return_value=mock_cosmos):
            resp = await list_feeds(_admin_req())

        body = json.loads(resp.get_body())
        assert body[0]["episodeCount"] == 5
        assert body[0]["processingCount"] == 0

    @pytest.mark.asyncio
    async def test_query_error_defaults_to_zero(self):
        from routes.feeds import list_feeds
        from azure.cosmos import CosmosClient

        feed_item = {**_mock_feed(), "_rid": "x", "_self": "x", "_etag": "x", "_attachments": "x", "_ts": 1}
        mock_feed_ctr = MagicMock()
        mock_feed_ctr.query_items.return_value = [feed_item]

        mock_sermon_ctr = MagicMock()
        mock_sermon_ctr.query_items.side_effect = Exception("cosmos error")
        mock_cosmos = MagicMock()
        mock_cosmos.get_database_client.return_value.get_container_client.return_value = mock_sermon_ctr

        with patch("routes.feeds._feeds_container", return_value=mock_feed_ctr), \
             patch.object(CosmosClient, "from_connection_string", return_value=mock_cosmos):
            resp = await list_feeds(_admin_req())

        body = json.loads(resp.get_body())
        assert body[0]["episodeCount"] == 0
        assert body[0]["processingCount"] == 0


# ── _poll_all_feeds: lastPollResult persistence (sermon-2sm) ──

class TestPollLastResult:
    @pytest.mark.asyncio
    async def test_persists_last_poll_result_on_success(self):
        feed = _mock_feed(last_polled="2026-03-01T00:00:00Z")
        mock_cosmos, mock_feed_ctr = _patch_cosmos([feed], existing_guids=["ep-1"])
        parsed = MagicMock()
        parsed.entries = [_mock_entry("ep-1")]  # already known, so 0 new
        p = _feed_patches(mock_cosmos, mock_feed_ctr, parsed=parsed)

        starter = AsyncMock()
        with contextlib.ExitStack() as stack:
            for ctx in p:
                stack.enter_context(ctx)
            await _poll_all_feeds(starter)

        # feed_doc should have been upserted with lastPollResult
        upserted = mock_feed_ctr.upsert_item.call_args[0][0]
        assert upserted["lastPollResult"]["new"] == 0
        assert upserted["lastPollResult"]["errors"] == 0
        assert "timestamp" in upserted["lastPollResult"]

    @pytest.mark.asyncio
    async def test_persists_last_poll_result_on_error(self):
        feed = _mock_feed()
        mock_cosmos, mock_feed_ctr = _patch_cosmos([feed])
        p = _feed_patches(mock_cosmos, mock_feed_ctr, parse_side_effect=Exception("boom"))

        starter = AsyncMock()
        with contextlib.ExitStack() as stack:
            for ctx in p:
                stack.enter_context(ctx)
            results = await _poll_all_feeds(starter)

        upserted = mock_feed_ctr.upsert_item.call_args[0][0]
        assert upserted["lastPollResult"]["new"] == 0
        assert upserted["lastPollResult"]["errors"] == 1

        assert results[0]["error"] == "boom"


# ── new_feed_doc schema (sermon-2sm) ──

class TestNewFeedDocSchema:
    def test_includes_last_poll_result_null(self):
        from schema import new_feed_doc
        doc = new_feed_doc("f1", "https://example.com/feed.xml", "Test")
        assert doc["lastPollResult"] is None

    def test_basic_fields(self):
        from schema import new_feed_doc
        doc = new_feed_doc("f1", "https://example.com/feed.xml", "Test", backfill=5)
        assert doc["id"] == "f1"
        assert doc["feedUrl"] == "https://example.com/feed.xml"
        assert doc["title"] == "Test"
        assert doc["backfillCount"] == 5
        assert doc["active"] is True
