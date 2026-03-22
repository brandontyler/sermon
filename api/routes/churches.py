"""Church CRUD endpoints."""

import logging
import os

import azure.functions as func

from helpers import _json_response, _require_admin

bp = func.Blueprint()
log = logging.getLogger(__name__)


@bp.route(route="churches", methods=["GET"])
@bp.function_name("list_churches")
async def list_churches(req: func.HttpRequest) -> func.HttpResponse:
    """GET /api/churches — List all churches with pastors and sermon stats."""
    from azure.cosmos import CosmosClient

    cosmos = CosmosClient.from_connection_string(os.environ["COSMOS_CONNECTION_STRING"])
    db = cosmos.get_database_client("psr")

    try:
        church_container = db.get_container_client("churches")
        churches = list(church_container.query_items(
            "SELECT * FROM c", enable_cross_partition_query=True
        ))
    except Exception:
        churches = []

    for c in churches:
        for key in ("_rid", "_self", "_etag", "_attachments", "_ts"):
            c.pop(key, None)

    sermon_container = db.get_container_client("sermons")
    sermons = list(sermon_container.query_items(
        "SELECT c.pastor, c.compositePsr, c.totalScore, c.status FROM c WHERE c.status = 'complete'",
        enable_cross_partition_query=True,
    ))
    pastor_stats = {}
    for s in sermons:
        p = s.get("pastor")
        if not p:
            continue
        if p not in pastor_stats:
            pastor_stats[p] = {"count": 0, "total": 0}
        pastor_stats[p]["count"] += 1
        score = s.get("totalScore") or s.get("compositePsr") or 0
        pastor_stats[p]["total"] += score

    for c in churches:
        for p in c.get("pastors", []):
            stats = pastor_stats.get(p["name"], {"count": 0, "total": 0})
            p["sermonCount"] = stats["count"]
            p["avgScore"] = round(stats["total"] / stats["count"], 1) if stats["count"] else None

    return _json_response(churches)


@bp.route(route="churches", methods=["POST"])
@bp.function_name("upsert_church")
async def upsert_church(req: func.HttpRequest) -> func.HttpResponse:
    """POST /api/churches — Create or update a church (admin only)."""
    from azure.cosmos import CosmosClient

    auth_err = _require_admin(req)
    if auth_err:
        return auth_err

    try:
        body = req.get_json()
    except Exception:
        return _json_response({"error": "Invalid JSON"}, 400)

    required = ["id", "name"]
    if not all(body.get(k) for k in required):
        return _json_response({"error": f"Required fields: {required}"}, 400)

    cosmos = CosmosClient.from_connection_string(os.environ["COSMOS_CONNECTION_STRING"])
    db = cosmos.get_database_client("psr")

    try:
        church_container = db.create_container_if_not_exists(id="churches", partition_key={"paths": ["/id"], "kind": "Hash"})
    except Exception:
        church_container = db.get_container_client("churches")

    church_container.upsert_item(body)
    log.info(f"[upsert_church] {body['id']}: {body['name']}")
    return _json_response(body)


@bp.route(route="churches/{church_id}", methods=["DELETE"])
@bp.function_name("delete_church")
async def delete_church(req: func.HttpRequest) -> func.HttpResponse:
    """DELETE /api/churches/{id} — Remove a church (admin only)."""
    from azure.cosmos import CosmosClient, exceptions

    auth_err = _require_admin(req)
    if auth_err:
        return auth_err

    church_id = req.route_params.get("church_id")
    cosmos = CosmosClient.from_connection_string(os.environ["COSMOS_CONNECTION_STRING"])
    try:
        container = cosmos.get_database_client("psr").get_container_client("churches")
        container.delete_item(church_id, partition_key=church_id)
    except exceptions.CosmosResourceNotFoundError:
        return _json_response({"error": "Church not found"}, 404)

    log.info(f"[delete_church] {church_id}")
    return _json_response({"deleted": church_id})
