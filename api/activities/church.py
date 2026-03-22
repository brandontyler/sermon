"""Church auto-creation activity."""

import os

from activities.helpers import _openai_client, log


def ensure_church(input_data):
    """Auto-create a church entry if the pastor doesn't have one."""
    import json as _json
    from azure.cosmos import CosmosClient
    from schema import UNASSIGNED_CHURCH_ID

    pastor = input_data.get("pastor")
    sermon_id = input_data.get("sermonId")

    cosmos = CosmosClient.from_connection_string(os.environ["COSMOS_CONNECTION_STRING"])
    db = cosmos.get_database_client("psr")
    try:
        church_container = db.create_container_if_not_exists(
            id="churches", partition_key={"paths": ["/id"], "kind": "Hash"},
        )
    except Exception:
        church_container = db.get_container_client("churches")

    try:
        church_container.read_item(UNASSIGNED_CHURCH_ID, partition_key=UNASSIGNED_CHURCH_ID)
    except Exception:
        try:
            church_container.create_item({
                "id": UNASSIGNED_CHURCH_ID, "name": "Church Unassigned",
                "city": "", "state": "", "url": "", "pastors": [], "autoCreated": True,
            })
        except Exception:
            pass

    def _set_sermon_church(church_id):
        if not sermon_id:
            return
        try:
            sermon_container = db.get_container_client("sermons")
            doc = sermon_container.read_item(sermon_id, partition_key=sermon_id)
            doc["churchId"] = church_id
            sermon_container.upsert_item(doc)
        except Exception as e:
            log.warning(f"[ensure_church] Failed to set churchId on {sermon_id}: {e}")

    def _assign_unassigned():
        _set_sermon_church(UNASSIGNED_CHURCH_ID)
        if pastor:
            try:
                ua = church_container.read_item(UNASSIGNED_CHURCH_ID, partition_key=UNASSIGNED_CHURCH_ID)
                if not any(p["name"] == pastor for p in ua.get("pastors", [])):
                    ua.setdefault("pastors", []).append({"name": pastor})
                    church_container.upsert_item(ua)
            except Exception:
                pass

    if not pastor:
        _set_sermon_church(UNASSIGNED_CHURCH_ID)
        return {"ok": True, "church": None, "created": False}

    existing = list(church_container.query_items(
        "SELECT c.id, c.name FROM c WHERE ARRAY_CONTAINS(c.pastors, {'name': @p}, true)",
        parameters=[{"name": "@p", "value": pastor}],
        enable_cross_partition_query=True,
    ))
    if existing:
        _set_sermon_church(existing[0]["id"])
        return {"ok": True, "church": existing[0]["name"], "created": False}

    client = _openai_client()
    resp = client.chat.completions.create(
        model="gpt-5-nano",
        messages=[
            {"role": "system", "content": "You identify which church a pastor serves at. Return JSON only."},
            {"role": "user", "content": f"""Who is pastor "{pastor}"? Return their primary church.

Return JSON: {{"name": "<church name>", "city": "<city>", "state": "<2-letter state>", "url": "<church website or null>", "confidence": "<high|medium|low>"}}

If you cannot confidently identify them, return: {{"name": null, "confidence": "low"}}"""},
        ],
        temperature=0,
        response_format={"type": "json_object"},
    )

    try:
        result = _json.loads(resp.choices[0].message.content)
    except Exception:
        log.warning(f"[ensure_church] LLM returned unparseable response for {pastor}")
        _assign_unassigned()
        return {"ok": True, "church": None, "created": False}

    if not result.get("name") or result.get("confidence") == "low":
        log.info(f"[ensure_church] Could not identify church for {pastor}")
        _assign_unassigned()
        return {"ok": True, "church": None, "created": False}

    church_id = result["name"].lower().replace(" ", "-").replace("'", "")
    doc = {
        "id": church_id, "name": result["name"],
        "city": result.get("city", ""), "state": result.get("state", ""),
        "url": result.get("url") or "", "pastors": [{"name": pastor}], "autoCreated": True,
    }

    try:
        church_container.create_item(doc)
        log.info(f"[ensure_church] Auto-created church '{result['name']}' for {pastor}")
        _set_sermon_church(church_id)
        return {"ok": True, "church": result["name"], "created": True}
    except Exception as e:
        if "Conflict" in type(e).__name__ or "409" in str(e):
            existing_doc = church_container.read_item(church_id, partition_key=church_id)
            pastors = existing_doc.get("pastors", [])
            if not any(p["name"] == pastor for p in pastors):
                pastors.append({"name": pastor})
                existing_doc["pastors"] = pastors
                church_container.upsert_item(existing_doc)
                log.info(f"[ensure_church] Added {pastor} to existing church '{existing_doc['name']}'")
            _set_sermon_church(church_id)
            return {"ok": True, "church": existing_doc["name"], "created": False}
        log.warning(f"[ensure_church] Failed to create church for {pastor}: {e}")
        _assign_unassigned()
        return {"ok": True, "church": None, "created": False}
