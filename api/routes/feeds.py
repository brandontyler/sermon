"""RSS feed subscription endpoints."""

import datetime
import json
import os
import uuid

import azure.functions as func
import azure.durable_functions as df

from log import log
from schema import new_sermon_doc, new_feed_doc
from helpers import _json_response, _require_admin, _feeds_container

bp = func.Blueprint()


@bp.route(route="feeds", methods=["GET"])
@bp.function_name("list_feeds")
async def list_feeds(req: func.HttpRequest) -> func.HttpResponse:
    """GET /api/feeds — List all RSS feed subscriptions. Page-level auth via SWA route config."""
    container = _feeds_container()
    items = list(container.query_items("SELECT * FROM c ORDER BY c.createdAt DESC", enable_cross_partition_query=True))
    for item in items:
        for key in ("_rid", "_self", "_etag", "_attachments", "_ts"):
            item.pop(key, None)

    from azure.cosmos import CosmosClient
    sermon_container = CosmosClient.from_connection_string(os.environ["COSMOS_CONNECTION_STRING"]).get_database_client("psr").get_container_client("sermons")
    for feed in items:
        try:
            rows = list(sermon_container.query_items(
                "SELECT c.status, COUNT(1) as cnt FROM c WHERE c.feedId = @fid GROUP BY c.status",
                parameters=[{"name": "@fid", "value": feed["id"]}],
                enable_cross_partition_query=True,
            ))
            counts = {r["status"]: r["cnt"] for r in rows}
            feed["episodeCount"] = counts.get("complete", 0)
            feed["processingCount"] = counts.get("processing", 0)
        except Exception:
            feed["episodeCount"] = 0
            feed["processingCount"] = 0

    return _json_response(items)


@bp.route(route="feeds", methods=["POST"])
@bp.function_name("create_feed")
async def create_feed(req: func.HttpRequest) -> func.HttpResponse:
    """POST /api/feeds — Subscribe to an RSS feed."""

    try:
        body = req.get_json()
    except Exception:
        return _json_response({"error": "Invalid JSON"}, 400)

    feed_url = body.get("feedUrl", "").strip()
    if not feed_url:
        return _json_response({"error": "feedUrl is required"}, 400)

    backfill = min(body.get("backfillCount", 0), 50)
    church_id = body.get("churchId") or None

    import feedparser
    parsed = feedparser.parse(feed_url)
    if not parsed.entries:
        return _json_response({"error": "No episodes found in feed. Check the URL."}, 400)

    title = body.get("title") or parsed.feed.get("title", feed_url)
    feed_id = f"feed-{uuid.uuid4().hex[:8]}"
    doc = new_feed_doc(feed_id, feed_url, title, backfill, church_id=church_id)
    _feeds_container().create_item(doc)

    log.info(f"[create_feed] {feed_id}: {title} ({feed_url}), backfill={backfill}")
    return _json_response(doc, 201)


@bp.route(route="feeds/{feed_id}", methods=["PATCH"])
@bp.function_name("update_feed")
async def update_feed(req: func.HttpRequest) -> func.HttpResponse:
    """PATCH /api/feeds/{id} — Toggle active/pause or update settings."""

    feed_id = req.route_params.get("feed_id")
    try:
        body = req.get_json()
    except Exception:
        return _json_response({"error": "Invalid JSON"}, 400)

    container = _feeds_container()
    from azure.cosmos import exceptions
    try:
        doc = container.read_item(feed_id, partition_key=feed_id)
    except exceptions.CosmosResourceNotFoundError:
        return _json_response({"error": "Feed not found"}, 404)

    for key in ("active", "title", "backfillCount", "churchId"):
        if key in body:
            doc[key] = body[key]
    container.upsert_item(doc)
    return _json_response({"id": feed_id, "active": doc["active"]})


@bp.route(route="feeds/{feed_id}", methods=["DELETE"])
@bp.function_name("delete_feed")
async def delete_feed(req: func.HttpRequest) -> func.HttpResponse:
    """DELETE /api/feeds/{id} — Remove a feed subscription."""

    feed_id = req.route_params.get("feed_id")
    container = _feeds_container()
    from azure.cosmos import exceptions
    try:
        container.delete_item(feed_id, partition_key=feed_id)
    except exceptions.CosmosResourceNotFoundError:
        return _json_response({"error": "Feed not found"}, 404)

    log.info(f"[delete_feed] {feed_id}")
    return _json_response({"deleted": feed_id})


@bp.route(route="feeds/poll", methods=["POST"])
@bp.durable_client_input(client_name="starter")
@bp.function_name("poll_feeds_manual")
async def poll_feeds_manual(req: func.HttpRequest, starter: df.DurableOrchestrationClient) -> func.HttpResponse:
    """POST /api/feeds/poll — Manually trigger feed polling."""
    body = req.get_body()
    feed_ids = None
    if body:
        try:
            feed_ids = json.loads(body).get("feedIds")
        except Exception:
            pass
    results = await _poll_all_feeds(starter, feed_ids=feed_ids)
    return _json_response({"polled": len(results), "results": results})


@bp.route(route="feeds/preview", methods=["GET"])
@bp.function_name("preview_feeds")
async def preview_feeds(req: func.HttpRequest) -> func.HttpResponse:
    """GET /api/feeds/preview — Preview new episode counts without submitting."""
    results = await _preview_feeds()
    total = sum(r["newCount"] for r in results)
    return _json_response({"feeds": results, "totalNew": total, "estimatedCost": round(total * 0.75, 2)})


async def _preview_feeds():
    """Count new episodes per active feed without submitting anything."""
    import feedparser
    from azure.cosmos import CosmosClient

    cosmos = CosmosClient.from_connection_string(os.environ["COSMOS_CONNECTION_STRING"])
    db = cosmos.get_database_client("psr")
    feed_container = _feeds_container()
    sermon_container = db.get_container_client("sermons")

    feeds = list(feed_container.query_items(
        "SELECT * FROM c WHERE c.active = true", enable_cross_partition_query=True
    ))

    results = []
    for feed_doc in feeds:
        feed_id = feed_doc["id"]
        try:
            parsed = feedparser.parse(feed_doc["feedUrl"])
            if not parsed.entries:
                results.append({"feedId": feed_id, "title": feed_doc.get("title", ""), "newCount": 0})
                continue

            existing = list(sermon_container.query_items(
                "SELECT c.feedGuid FROM c WHERE c.feedId = @fid",
                parameters=[{"name": "@fid", "value": feed_id}],
                enable_cross_partition_query=True,
            ))
            known_guids = {e["feedGuid"] for e in existing if e.get("feedGuid")}

            entries = parsed.entries
            if not feed_doc.get("lastPolledAt") and feed_doc.get("backfillCount", 0) > 0:
                entries = entries[:feed_doc["backfillCount"]]
            elif feed_doc.get("lastPolledAt"):
                from email.utils import parsedate_to_datetime
                sub_dt = datetime.datetime.fromisoformat(feed_doc["createdAt"].replace("Z", "+00:00"))
                entries = [e for e in entries if e.get("published_parsed") and
                    datetime.datetime(*e["published_parsed"][:6], tzinfo=datetime.timezone.utc) >= sub_dt]

            new_count = 0
            for entry in entries:
                guid = entry.get("id") or entry.get("link", "")
                if guid in known_guids:
                    continue
                has_audio = any(enc.get("type", "").startswith("audio/") for enc in entry.get("enclosures", []))
                if not has_audio:
                    has_audio = any(link.get("type", "").startswith("audio/") for link in entry.get("links", []))
                if has_audio:
                    new_count += 1

            results.append({"feedId": feed_id, "title": feed_doc.get("title", ""), "newCount": new_count})
        except Exception as e:
            log.error(f"[preview_feed] {feed_id} failed: {e}", exc_info=True)
            results.append({"feedId": feed_id, "title": feed_doc.get("title", ""), "newCount": 0, "error": str(e)})

    return results


@bp.timer_trigger(schedule="0 0 */12 * * *", arg_name="timer", run_on_startup=False)
@bp.durable_client_input(client_name="starter")
@bp.function_name("poll_feeds_timer")
async def poll_feeds_timer(timer: func.TimerRequest, starter: df.DurableOrchestrationClient):
    """Timer: poll RSS feeds every 12 hours."""
    if timer.past_due:
        log.info("[poll_feeds_timer] Timer is past due, running anyway")
    results = await _poll_all_feeds(starter)
    log.info(f"[poll_feeds_timer] Polled feeds, submitted {sum(r.get('new', 0) for r in results)} new episodes")


async def _poll_all_feeds(starter: df.DurableOrchestrationClient, feed_ids=None):
    """Poll active feeds, submit new episodes for scoring. Optionally filter by feed_ids."""
    import feedparser
    from azure.cosmos import CosmosClient

    cosmos = CosmosClient.from_connection_string(os.environ["COSMOS_CONNECTION_STRING"])
    db = cosmos.get_database_client("psr")
    feed_container = _feeds_container()
    sermon_container = db.get_container_client("sermons")

    feeds = list(feed_container.query_items(
        "SELECT * FROM c WHERE c.active = true", enable_cross_partition_query=True
    ))
    if feed_ids:
        feed_ids_set = set(feed_ids)
        feeds = [f for f in feeds if f["id"] in feed_ids_set]

    log.info(f"[poll_feeds] polling {len(feeds)} active feed(s)")
    results = []
    for feed_doc in feeds:
        feed_id = feed_doc["id"]
        try:
            parsed = feedparser.parse(feed_doc["feedUrl"])
            if not parsed.entries:
                log.warning(f"[poll_feed] {feed_id}: no entries in feed")
                results.append({"feedId": feed_id, "new": 0, "error": "No entries"})
                continue

            existing = list(sermon_container.query_items(
                "SELECT c.feedGuid FROM c WHERE c.feedId = @fid",
                parameters=[{"name": "@fid", "value": feed_id}],
                enable_cross_partition_query=True,
            ))
            known_guids = {e["feedGuid"] for e in existing if e.get("feedGuid")}

            entries = parsed.entries
            if not feed_doc.get("lastPolledAt") and feed_doc.get("backfillCount", 0) > 0:
                entries = entries[:feed_doc["backfillCount"]]
            elif feed_doc.get("lastPolledAt"):
                from email.utils import parsedate_to_datetime
                sub_dt = datetime.datetime.fromisoformat(feed_doc["createdAt"].replace("Z", "+00:00"))
                filtered = []
                for e in entries:
                    pub = e.get("published_parsed")
                    if pub:
                        pub_dt = datetime.datetime(*pub[:6], tzinfo=datetime.timezone.utc)
                        if pub_dt >= sub_dt:
                            filtered.append(e)
                entries = filtered

            new_count = 0
            for entry in entries:
                guid = entry.get("id") or entry.get("link", "")
                if guid in known_guids:
                    continue

                audio_url = None
                for enc in entry.get("enclosures", []):
                    if enc.get("type", "").startswith("audio/"):
                        audio_url = enc.get("href") or enc.get("url")
                        break
                if not audio_url:
                    for link in entry.get("links", []):
                        if link.get("type", "").startswith("audio/"):
                            audio_url = link.get("href")
                            break
                if not audio_url:
                    continue

                sermon_id = str(uuid.uuid4())
                title = entry.get("title", "Untitled Episode")
                pastor = entry.get("author") or None
                pub = entry.get("published_parsed")
                date = f"{pub.tm_year}-{pub.tm_mon:02d}-{pub.tm_mday:02d}" if pub else None
                doc = new_sermon_doc(sermon_id, f"rss-{feed_id}", title, pastor=pastor)
                if date:
                    doc["date"] = date
                doc["feedId"] = feed_id
                doc["feedGuid"] = guid
                doc["inputType"] = "rss"
                doc["uploadedAt"] = datetime.datetime.utcnow().isoformat() + "Z"
                doc["rssAudioUrl"] = audio_url
                if feed_doc.get("churchId"):
                    doc["churchId"] = feed_doc["churchId"]
                doc["rssMeta"] = {
                    "subtitle": entry.get("subtitle") or None,
                    "summary": entry.get("summary") or None,
                    "link": entry.get("link") or None,
                    "image": (entry.get("image") or {}).get("href") or None,
                }
                sermon_container.create_item(doc)

                await starter.start_new("rss_sermon_orchestrator", client_input={
                    "sermonId": sermon_id,
                    "audioUrl": audio_url,
                    "userTitle": title,
                    "userPastor": pastor,
                    "churchId": feed_doc.get("churchId"),
                })
                new_count += 1
                known_guids.add(guid)
                log.info(f"[poll_feed] {feed_id}: submitted '{title}' ({sermon_id})")

            feed_doc["lastPolledAt"] = datetime.datetime.utcnow().isoformat() + "Z"
            feed_doc["lastPollResult"] = {"new": new_count, "errors": 0, "timestamp": feed_doc["lastPolledAt"]}
            if entries:
                feed_doc["lastSeenGuid"] = entries[0].get("id") or entries[0].get("link", "")
            feed_container.upsert_item(feed_doc)
            log.info(f"[poll_feed] {feed_id}: {new_count} new episode(s)")
            results.append({"feedId": feed_id, "new": new_count})

        except Exception as e:
            log.error(f"[poll_feed] {feed_id} failed: {e}", exc_info=True)
            feed_doc["lastPollResult"] = {"new": 0, "errors": 1, "timestamp": datetime.datetime.utcnow().isoformat() + "Z"}
            try:
                feed_container.upsert_item(feed_doc)
            except Exception:
                pass
            results.append({"feedId": feed_id, "new": 0, "error": str(e)})

    total_new = sum(r.get("new", 0) for r in results)
    total_err = sum(1 for r in results if "error" in r)
    log.info(f"[poll_feeds] done — {total_new} new episode(s), {total_err} error(s)")
    return results
