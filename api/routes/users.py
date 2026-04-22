"""User account routes — GET/POST /api/account."""

import os
import json
from datetime import datetime, timezone

import azure.functions as func

bp = func.Blueprint()


def _json_response(body, status_code=200, headers=None):
    h = {"Content-Type": "application/json"}
    if headers:
        h.update(headers)
    return func.HttpResponse(json.dumps(body, default=str), status_code=status_code, headers=h)


def _get_user_from_header(req: func.HttpRequest):
    """Extract user info from SWA EasyAuth header."""
    import base64
    principal = req.headers.get("x-ms-client-principal")
    if not principal:
        return None
    decoded = json.loads(base64.b64decode(principal))
    claims = {c["typ"]: c["val"] for c in decoded.get("claims", [])}
    return {
        "userId": decoded.get("userId"),
        "name": claims.get("name", claims.get("http://schemas.xmlsoap.org/ws/2005/05/identity/claims/name", "")),
        "email": claims.get("http://schemas.xmlsoap.org/ws/2005/05/identity/claims/emailaddress", claims.get("preferred_username", "")),
        "provider": decoded.get("identityProvider", ""),
    }


def _get_user_id(req: func.HttpRequest):
    """Get user ID from auth header or query/body fallback."""
    user = _get_user_from_header(req)
    if user and user.get("userId"):
        return user["userId"], user.get("email", ""), user.get("provider", "")
    # Fallback: client passes userId from /.auth/me
    uid = req.params.get("userId")
    if uid:
        return uid, req.params.get("email", ""), "aad"
    return None, None, None


def _users_container():
    from azure.cosmos import CosmosClient
    cosmos = CosmosClient.from_connection_string(os.environ["COSMOS_CONNECTION_STRING"])
    return cosmos.get_database_client("psr").get_container_client("users")


@bp.route(route="account", methods=["GET"])
@bp.function_name("get_account")
async def get_account(req: func.HttpRequest) -> func.HttpResponse:
    """GET /api/account?userId=...&email=... — Get or create user account."""
    user_id, email, provider = _get_user_id(req)
    if not user_id:
        return _json_response({"error": "Not authenticated"}, 401)

    container = _users_container()
    try:
        doc = container.read_item(item=user_id, partition_key=user_id)
        if email and doc.get("email") != email:
            doc["email"] = email
            container.upsert_item(doc)
        return _json_response(doc)
    except Exception:
        now = datetime.now(timezone.utc).isoformat()
        doc = {
            "id": user_id,
            "name": "",
            "email": email or "",
            "phone": "",
            "provider": provider or "",
            "joinedAt": now,
            "uploadsUsed": 0,
            "uploadsLimit": 3,
            "trialDays": 30,
        }
        container.upsert_item(doc)
        return _json_response(doc, 201)


@bp.route(route="account", methods=["POST"])
@bp.function_name("update_account")
async def update_account(req: func.HttpRequest) -> func.HttpResponse:
    """POST /api/account — Update user profile."""
    body = req.get_json()
    user_id, _, _ = _get_user_id(req)
    if not user_id:
        user_id = body.get("userId")
    if not user_id:
        return _json_response({"error": "Not authenticated"}, 401)

    container = _users_container()
    try:
        doc = container.read_item(item=user_id, partition_key=user_id)
    except Exception:
        now = datetime.now(timezone.utc).isoformat()
        doc = {"id": user_id, "name": "", "email": body.get("email", ""), "phone": "", "provider": "aad", "joinedAt": now, "uploadsUsed": 0, "uploadsLimit": 3, "trialDays": 30}

    if "name" in body:
        doc["name"] = body["name"]
    if "phone" in body:
        doc["phone"] = body["phone"]
    if "email" in body and body["email"]:
        doc["email"] = body["email"]
    container.upsert_item(doc)
    return _json_response(doc)
