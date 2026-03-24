"""Admin endpoints (rescore)."""

import azure.functions as func
import azure.durable_functions as df

from log import log
from helpers import _json_response, _require_admin

bp = func.Blueprint()


@bp.route(route="rescore", methods=["POST"], auth_level=func.AuthLevel.ANONYMOUS)
@bp.durable_client_input(client_name="starter")
@bp.function_name("admin_rescore")
async def admin_rescore(req: func.HttpRequest, starter: df.DurableOrchestrationClient) -> func.HttpResponse:
    """POST /api/admin/rescore — Re-score sermons with current models. Requires admin key."""
    import os
    from azure.cosmos import CosmosClient

    auth_err = _require_admin(req)
    if auth_err:
        return auth_err
    body = req.get_json() if req.get_body() else {}
    sermon_ids = body.get("sermonIds")
    rescore_all = body.get("all", False)
    older_than = body.get("olderThan")
    passes = body.get("passes")
    stale_only = body.get("staleOnly", False)

    if stale_only:
        passes = ["stale"]

    if not sermon_ids and not rescore_all:
        return _json_response({"error": "Provide sermonIds array or {\"all\": true}"}, 400)

    cosmos = CosmosClient.from_connection_string(os.environ["COSMOS_CONNECTION_STRING"])
    container = cosmos.get_database_client("psr").get_container_client("sermons")

    if rescore_all:
        if older_than:
            query = "SELECT c.id FROM c WHERE c.status = 'complete' AND (NOT IS_DEFINED(c.pipelineVersion) OR c.pipelineVersion < @v)"
            items = list(container.query_items(query, parameters=[{"name": "@v", "value": older_than}], enable_cross_partition_query=True))
        else:
            items = list(container.query_items("SELECT c.id FROM c WHERE c.status = 'complete'", enable_cross_partition_query=True))
        sermon_ids = [item["id"] for item in items]

    if not sermon_ids:
        return _json_response({"message": "No sermons to rescore", "count": 0})

    instance_id = await starter.start_new("rescore_orchestrator", client_input={"sermonIds": sermon_ids, "passes": passes})
    log.info(f"[admin_rescore] Started rescore orchestrator {instance_id} for {len(sermon_ids)} sermons, passes={passes}")
    return _json_response({"instanceId": instance_id, "count": len(sermon_ids), "sermonIds": sermon_ids, "passes": passes}, 202)
