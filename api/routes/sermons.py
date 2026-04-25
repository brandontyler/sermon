"""Sermon CRUD + upload endpoints."""

import os
import uuid

import azure.functions as func
import azure.durable_functions as df

from log import log
from schema import new_sermon_doc, fail_sermon_doc
from helpers import (
    ALLOWED_TYPES, MAX_SIZE, ALLOWED_TEXT_TYPES, ALLOWED_TEXT_EXTENSIONS, MAX_TEXT_SIZE,
    _json_response, _require_admin, _extract_text, _extract_video_id, _parse_timestamp,
)

bp = func.Blueprint()


@bp.route(route="sermons/{sermon_id}/cbv", methods=["GET"])
@bp.function_name("get_cbv_score")
async def get_cbv_score(req: func.HttpRequest) -> func.HttpResponse:
    """GET /api/sermons/{id}/cbv — Check which church beliefs are referenced in the sermon."""
    from azure.cosmos import CosmosClient, exceptions

    sermon_id = req.route_params.get("sermon_id")
    cosmos = CosmosClient.from_connection_string(os.environ["COSMOS_CONNECTION_STRING"])
    db = cosmos.get_database_client("psr")

    # Get sermon
    try:
        sermon = db.get_container_client("sermons").read_item(sermon_id, partition_key=sermon_id)
    except exceptions.CosmosResourceNotFoundError:
        return _json_response({"error": "Sermon not found"}, 404)

    # Return cached result if available
    if sermon.get("cbv"):
        return _json_response(sermon["cbv"], headers={"Cache-Control": "public, max-age=3600"})

    transcript = (sermon.get("transcript") or {}).get("fullText", "")
    if not transcript:
        return _json_response({"error": "No transcript available"}, 400)

    # Find matching church via pastor
    pastor = sermon.get("pastor")
    if not pastor:
        return _json_response({"error": "No pastor linked"}, 400)

    try:
        churches = list(db.get_container_client("churches").query_items(
            "SELECT * FROM c", enable_cross_partition_query=True
        ))
    except Exception:
        churches = []

    church = next((c for c in churches if any(p["name"] == pastor for p in c.get("pastors", []))), None)
    if not church or not church.get("beliefs"):
        return _json_response({"error": "No church beliefs found"}, 400)

    beliefs = church["beliefs"]
    # Build belief list for the prompt
    belief_lines = "\n".join(f"- {b['title']}: {b.get('description', '')}" for b in beliefs if isinstance(b, dict))
    if not belief_lines:
        # Legacy format (list of strings)
        belief_lines = "\n".join(f"- {b}" for b in beliefs if isinstance(b, str))

    # Truncate transcript to ~4000 words to stay within token limits
    words = transcript.split()
    truncated = " ".join(words[:4000])

    from activities.helpers import _openai_client
    client = _openai_client()

    resp = client.chat.completions.create(
        model="gpt-5-nano",
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": "You check whether a sermon references specific church beliefs/values. "
             "For each belief, determine if the sermon meaningfully touches on that theme — "
             "it doesn't need to quote it verbatim, just clearly relate to the concept. "
             "Return JSON: {\"results\": [{\"title\": \"...\", \"referenced\": true/false}]}"},
            {"role": "user", "content": f"Church beliefs:\n{belief_lines}\n\nSermon transcript:\n{truncated}"},
        ],
    )

    import json
    try:
        cbv = json.loads(resp.choices[0].message.content)
    except Exception:
        return _json_response({"error": "AI response parse error"}, 500)

    # Cache on sermon doc
    try:
        sermon["cbv"] = cbv
        db.get_container_client("sermons").upsert_item(sermon)
    except Exception:
        pass  # non-fatal

    return _json_response(cbv, headers={"Cache-Control": "public, max-age=3600"})


@bp.route(route="sermons", methods=["POST"])
@bp.durable_client_input(client_name="starter")
@bp.function_name("upload_sermon")
async def upload_sermon(req: func.HttpRequest, starter: df.DurableOrchestrationClient) -> func.HttpResponse:
    """POST /api/sermons — Upload audio and start processing."""
    import datetime
    from azure.cosmos import CosmosClient
    from azure.storage.blob import BlobClient

    content_length = req.headers.get("Content-Length")
    if content_length and int(content_length) > MAX_SIZE:
        return _json_response({"error": "File too large. Max 100MB."}, 413)

    cosmos = CosmosClient.from_connection_string(os.environ["COSMOS_CONNECTION_STRING"])
    container = cosmos.get_database_client("psr").get_container_client("sermons")

    MAX_CONCURRENT = 3
    try:
        processing = list(container.query_items(
            "SELECT VALUE COUNT(1) FROM c WHERE c.status = 'processing'",
            enable_cross_partition_query=True,
        ))
        if processing and processing[0] >= MAX_CONCURRENT:
            log.warning(f"[upload] Rejected — {processing[0]} sermons already processing")
            return _json_response({"error": "Server is busy processing other sermons. Please try again in a few minutes."}, 429)
    except Exception as e:
        log.warning(f"[upload] Concurrency check failed ({e}), allowing upload")

    MAX_UPLOADS_PER_HOUR = 5
    client_ip = req.headers.get("X-Forwarded-For", req.headers.get("REMOTE_ADDR", "unknown"))
    if "," in client_ip:
        client_ip = client_ip.split(",")[0].strip()
    try:
        one_hour_ago = (datetime.datetime.utcnow() - datetime.timedelta(hours=1)).isoformat() + "Z"
        recent = list(container.query_items(
            "SELECT VALUE COUNT(1) FROM c WHERE c.uploaderIp = @ip AND c.uploadedAt > @since",
            parameters=[{"name": "@ip", "value": client_ip}, {"name": "@since", "value": one_hour_ago}],
            enable_cross_partition_query=True,
        ))
        if recent and recent[0] >= MAX_UPLOADS_PER_HOUR:
            log.warning(f"[upload] Rate limited IP {client_ip} ({recent[0]} uploads in last hour)")
            return _json_response({"error": "Upload limit reached. Try again in an hour."}, 429)
    except Exception as e:
        log.warning(f"[upload] Rate limit check failed ({e}), allowing upload")

    file = req.files.get("file")
    if not file:
        return _json_response({"error": "No file uploaded"}, 400)

    content_type = file.content_type or ""
    if content_type not in ALLOWED_TYPES:
        return _json_response({"error": "Unsupported format. Upload MP3, WAV, or M4A."}, 400)

    audio_bytes = file.read()
    if len(audio_bytes) > MAX_SIZE:
        return _json_response({"error": "File too large. Max 100MB."}, 400)

    title = req.form.get("title") or None
    pastor = req.form.get("pastor") or None
    sermon_id = str(uuid.uuid4())
    filename = file.filename or f"sermon{ALLOWED_TYPES.get(content_type, '.mp3')}"
    blob_name = f"{sermon_id}/{filename}"

    try:
        blob = BlobClient.from_connection_string(
            os.environ["STORAGE_CONNECTION_STRING"], "sermon-audio", blob_name
        )
        blob.upload_blob(audio_bytes, content_type=content_type)
    except Exception as e:
        log.error(f"[upload] Blob upload failed for {sermon_id}: {e}", exc_info=True)
        return _json_response({"error": "Failed to store audio file. Please retry."}, 500)

    doc = new_sermon_doc(sermon_id, filename, title, pastor)
    doc["blobUrl"] = blob_name
    doc["uploaderIp"] = client_ip
    doc["uploadedAt"] = datetime.datetime.utcnow().isoformat() + "Z"
    try:
        container.create_item(doc)
    except Exception as e:
        log.error(f"[upload] Cosmos create failed for {sermon_id}: {e}", exc_info=True)
        return _json_response({"error": "Failed to create sermon record. Please retry."}, 500)

    try:
        instance_id = await starter.start_new("sermon_orchestrator", client_input={
            "sermonId": sermon_id,
            "blobUrl": blob_name,
            "userTitle": title,
            "userPastor": pastor,
        })
        log.info(f"[upload] Started orchestrator {instance_id} for sermon {sermon_id}")
    except Exception as e:
        log.error(f"[upload] Orchestrator start failed for {sermon_id}: {e}", exc_info=True)
        try:
            container.upsert_item({**doc, **fail_sermon_doc("Orchestrator failed to start — please re-upload")})
        except Exception:
            pass
        return _json_response({"error": "Processing failed to start. Please retry."}, 500)

    return _json_response({"id": sermon_id, "status": "processing"}, 202)


@bp.route(route="sermons/text", methods=["POST"])
@bp.durable_client_input(client_name="starter")
@bp.function_name("upload_text_sermon")
async def upload_text_sermon(req: func.HttpRequest, starter: df.DurableOrchestrationClient) -> func.HttpResponse:
    """POST /api/sermons/text — Upload text transcript and start processing (skip transcription + audio)."""
    import datetime
    from azure.cosmos import CosmosClient

    cosmos = CosmosClient.from_connection_string(os.environ["COSMOS_CONNECTION_STRING"])
    container = cosmos.get_database_client("psr").get_container_client("sermons")

    MAX_CONCURRENT = 3
    try:
        processing = list(container.query_items(
            "SELECT VALUE COUNT(1) FROM c WHERE c.status = 'processing'",
            enable_cross_partition_query=True,
        ))
        if processing and processing[0] >= MAX_CONCURRENT:
            return _json_response({"error": "Server is busy processing other sermons. Please try again in a few minutes."}, 429)
    except Exception:
        pass

    MAX_UPLOADS_PER_HOUR = 5
    client_ip = req.headers.get("X-Forwarded-For", req.headers.get("REMOTE_ADDR", "unknown"))
    if "," in client_ip:
        client_ip = client_ip.split(",")[0].strip()
    try:
        one_hour_ago = (datetime.datetime.utcnow() - datetime.timedelta(hours=1)).isoformat() + "Z"
        recent = list(container.query_items(
            "SELECT VALUE COUNT(1) FROM c WHERE c.uploaderIp = @ip AND c.uploadedAt > @since",
            parameters=[{"name": "@ip", "value": client_ip}, {"name": "@since", "value": one_hour_ago}],
            enable_cross_partition_query=True,
        ))
        if recent and recent[0] >= MAX_UPLOADS_PER_HOUR:
            return _json_response({"error": "Upload limit reached. Try again in an hour."}, 429)
    except Exception:
        pass

    file = req.files.get("file")
    if not file:
        return _json_response({"error": "No file uploaded"}, 400)

    filename = file.filename or "sermon.txt"
    ext = os.path.splitext(filename)[1].lower()
    content_type = file.content_type or ""

    if ext not in ALLOWED_TEXT_EXTENSIONS and content_type not in ALLOWED_TEXT_TYPES:
        return _json_response({"error": f"Unsupported format. Upload TXT, DOCX, MD, RTF, ODT, HTML, or CSV."}, 400)

    file_bytes = file.read()
    if len(file_bytes) > MAX_TEXT_SIZE:
        return _json_response({"error": "File too large. Max 10MB for text files."}, 400)

    try:
        transcript_text = _extract_text(file_bytes, filename, content_type)
    except ValueError as e:
        return _json_response({"error": str(e)}, 400)

    word_count = len(transcript_text.split())
    if word_count < 50:
        return _json_response({"error": "Transcript too short (under 50 words). Upload a complete sermon."}, 400)

    title = req.form.get("title") or None
    pastor = req.form.get("pastor") or None
    sermon_id = str(uuid.uuid4())

    doc = new_sermon_doc(sermon_id, filename, title, pastor)
    doc["uploaderIp"] = client_ip
    doc["uploadedAt"] = datetime.datetime.utcnow().isoformat() + "Z"
    doc["inputType"] = "text"
    try:
        container.create_item(doc)
    except Exception as e:
        log.error(f"[upload_text] Cosmos create failed for {sermon_id}: {e}", exc_info=True)
        return _json_response({"error": "Failed to create sermon record. Please retry."}, 500)

    try:
        instance_id = await starter.start_new("text_sermon_orchestrator", client_input={
            "sermonId": sermon_id,
            "transcript": transcript_text,
            "wordCount": word_count,
            "userTitle": title,
            "userPastor": pastor,
        })
        log.info(f"[upload_text] Started text orchestrator {instance_id} for sermon {sermon_id}")
    except Exception as e:
        log.error(f"[upload_text] Orchestrator start failed for {sermon_id}: {e}", exc_info=True)
        try:
            container.upsert_item({**doc, **fail_sermon_doc("Orchestrator failed to start — please re-upload")})
        except Exception:
            pass
        return _json_response({"error": "Processing failed to start. Please retry."}, 500)

    return _json_response({"id": sermon_id, "status": "processing"}, 202)


@bp.route(route="sermons/youtube", methods=["POST"])
@bp.durable_client_input(client_name="starter")
@bp.function_name("upload_youtube_sermon")
async def upload_youtube_sermon(req: func.HttpRequest, starter: df.DurableOrchestrationClient) -> func.HttpResponse:
    """POST /api/sermons/youtube — Fetch YouTube transcript and start processing."""
    import datetime
    from azure.cosmos import CosmosClient

    try:
        body = req.get_json()
    except Exception:
        return _json_response({"error": "Invalid JSON"}, 400)

    url = body.get("url", "").strip()
    video_id = _extract_video_id(url)
    if not video_id:
        return _json_response({"error": "Invalid YouTube URL"}, 400)

    start_sec = _parse_timestamp(body.get("start", ""))
    end_sec = _parse_timestamp(body.get("end", ""))
    if start_sec is None or end_sec is None:
        return _json_response({"error": "Start and end timestamps are required (format: H:MM:SS)"}, 400)
    if end_sec <= start_sec:
        return _json_response({"error": "End time must be after start time"}, 400)

    cosmos = CosmosClient.from_connection_string(os.environ["COSMOS_CONNECTION_STRING"])
    container = cosmos.get_database_client("psr").get_container_client("sermons")

    MAX_CONCURRENT = 3
    try:
        processing = list(container.query_items(
            "SELECT VALUE COUNT(1) FROM c WHERE c.status = 'processing'",
            enable_cross_partition_query=True,
        ))
        if processing and processing[0] >= MAX_CONCURRENT:
            return _json_response({"error": "Server is busy processing other sermons. Please try again in a few minutes."}, 429)
    except Exception:
        pass

    client_ip = req.headers.get("X-Forwarded-For", req.headers.get("REMOTE_ADDR", "unknown"))
    if "," in client_ip:
        client_ip = client_ip.split(",")[0].strip()
    try:
        one_hour_ago = (datetime.datetime.utcnow() - datetime.timedelta(hours=1)).isoformat() + "Z"
        recent = list(container.query_items(
            "SELECT VALUE COUNT(1) FROM c WHERE c.uploaderIp = @ip AND c.uploadedAt > @since",
            parameters=[{"name": "@ip", "value": client_ip}, {"name": "@since", "value": one_hour_ago}],
            enable_cross_partition_query=True,
        ))
        if recent and recent[0] >= 5:
            return _json_response({"error": "Upload limit reached. Try again in an hour."}, 429)
    except Exception:
        pass

    try:
        from youtube_transcript_api import YouTubeTranscriptApi
        from youtube_transcript_api.proxies import WebshareProxyConfig

        proxy_user = os.environ.get("WEBSHARE_PROXY_USERNAME", "")
        proxy_pass = os.environ.get("WEBSHARE_PROXY_PASSWORD", "")

        if proxy_user and proxy_pass:
            ytt = YouTubeTranscriptApi(proxy_config=WebshareProxyConfig(
                proxy_username=proxy_user, proxy_password=proxy_pass,
            ))
        else:
            ytt = YouTubeTranscriptApi()

        # Retry up to 3 times — proxy rotates IPs, so a fresh attempt may succeed
        import time as _time
        last_err = None
        for attempt in range(3):
            try:
                fetched = ytt.fetch(video_id, languages=["en"])
                last_err = None
                break
            except Exception as fetch_err:
                last_err = fetch_err
                if attempt < 2:
                    log.info(f"[upload_youtube] Attempt {attempt+1} failed for {video_id}, retrying: {fetch_err}")
                    _time.sleep(1)
        if last_err:
            raise last_err

        filtered = [s for s in fetched if s.start >= start_sec and s.start < end_sec]
        if not filtered:
            return _json_response({"error": f"No transcript found between {body.get('start')} and {body.get('end')}. Check your timestamps."}, 400)
        transcript_text = " ".join(s.text for s in filtered)
    except Exception as e:
        err_str = str(e).lower()
        log.warning(f"[upload_youtube] Failed to fetch transcript for {video_id}: {e}")
        if any(kw in err_str for kw in ("blocking", "blocked", "requestblocked", "ipblocked", "429", "/sorry", "max retries")):
            return _json_response({
                "error": "YouTube is blocking our server. Please use the text upload instead — open the YouTube video, click '...' → 'Show transcript', copy the text, paste it into a .txt file, and upload it.",
                "code": "IP_BLOCKED",
            }, 400)
        return _json_response({"error": "Could not fetch transcript. The video may not have English captions, or the URL may be invalid."}, 400)

    word_count = len(transcript_text.split())
    if word_count < 50:
        return _json_response({"error": "Transcript too short (under 50 words). Try a different video."}, 400)

    title = body.get("title") or None
    pastor = body.get("pastor") or None
    sermon_id = str(uuid.uuid4())

    doc = new_sermon_doc(sermon_id, f"youtube-{video_id}", title, pastor)
    doc["uploaderIp"] = client_ip
    doc["uploadedAt"] = datetime.datetime.utcnow().isoformat() + "Z"
    doc["inputType"] = "youtube"
    doc["youtubeVideoId"] = video_id
    doc["youtubeUrl"] = f"https://www.youtube.com/watch?v={video_id}"
    doc["youtubeStart"] = start_sec
    doc["youtubeEnd"] = end_sec
    try:
        container.create_item(doc)
    except Exception as e:
        log.error(f"[upload_youtube] Cosmos create failed for {sermon_id}: {e}", exc_info=True)
        return _json_response({"error": "Failed to create sermon record. Please retry."}, 500)

    try:
        instance_id = await starter.start_new("text_sermon_orchestrator", client_input={
            "sermonId": sermon_id,
            "transcript": transcript_text,
            "wordCount": word_count,
            "userTitle": title,
            "userPastor": pastor,
        })
        log.info(f"[upload_youtube] Started orchestrator {instance_id} for sermon {sermon_id} (video {video_id}, {word_count} words)")
    except Exception as e:
        log.error(f"[upload_youtube] Orchestrator start failed for {sermon_id}: {e}", exc_info=True)
        try:
            container.upsert_item({**doc, **fail_sermon_doc("Orchestrator failed to start — please re-upload")})
        except Exception:
            pass
        return _json_response({"error": "Processing failed to start. Please retry."}, 500)

    return _json_response({"id": sermon_id, "status": "processing"}, 202)


@bp.route(route="sermons", methods=["GET"])
@bp.function_name("list_sermons")
async def list_sermons(req: func.HttpRequest) -> func.HttpResponse:
    """GET /api/sermons — Feed list. x-tenant header filters by churchId."""
    from azure.cosmos import CosmosClient

    cosmos = CosmosClient.from_connection_string(os.environ["COSMOS_CONNECTION_STRING"])
    container = cosmos.get_database_client("psr").get_container_client("sermons")

    tenant = req.headers.get("x-tenant")
    if tenant:
        query = "SELECT c.id, c.title, c.pastor, c.date, c.duration, c.status, c.sermonType, c.compositePsr, c.inputType, c.bonus, c.totalScore FROM c WHERE c.churchId = @churchId ORDER BY c.date DESC"
        items = list(container.query_items(query, parameters=[{"name": "@churchId", "value": tenant}], enable_cross_partition_query=True))
    else:
        query = "SELECT c.id, c.title, c.pastor, c.date, c.duration, c.status, c.sermonType, c.compositePsr, c.inputType, c.bonus, c.totalScore FROM c ORDER BY c.date DESC"
        items = list(container.query_items(query, enable_cross_partition_query=True))

    return _json_response(items, headers={"Cache-Control": "public, max-age=30"})


@bp.route(route="sermons/dashboard", methods=["GET"])
@bp.function_name("dashboard_sermons")
async def dashboard_sermons(req: func.HttpRequest) -> func.HttpResponse:
    """GET /api/sermons/dashboard — Aggregated data for dashboard (single call replaces N+1)."""
    from azure.cosmos import CosmosClient

    cosmos = CosmosClient.from_connection_string(os.environ["COSMOS_CONNECTION_STRING"])
    container = cosmos.get_database_client("psr").get_container_client("sermons")

    tenant = req.headers.get("x-tenant")
    # Select only fields the dashboard needs — excludes transcript (70KB per sermon)
    fields = "c.id, c.title, c.pastor, c.date, c.duration, c.compositePsr, c.totalScore, c.status, c.sermonType, c.categories, c.strengths, c.improvements, c.enrichment, c.cbv, c.inputType"
    if tenant:
        query = f"SELECT {fields} FROM c WHERE c.status = 'complete' AND c.churchId = @churchId ORDER BY c.date DESC"
        items = list(container.query_items(query, parameters=[{"name": "@churchId", "value": tenant}], enable_cross_partition_query=True))
    else:
        query = f"SELECT {fields} FROM c WHERE c.status = 'complete' ORDER BY c.date DESC"
        items = list(container.query_items(query, enable_cross_partition_query=True))

    return _json_response(items, headers={"Cache-Control": "public, max-age=30"})


@bp.route(route="sermons/{sermon_id}", methods=["GET"])
@bp.function_name("get_sermon")
async def get_sermon(req: func.HttpRequest) -> func.HttpResponse:
    """GET /api/sermons/{id} — Sermon detail. Excludes transcript by default for performance."""
    from azure.cosmos import CosmosClient, exceptions

    sermon_id = req.route_params.get("sermon_id")
    include_transcript = req.params.get("include") == "transcript"
    cosmos = CosmosClient.from_connection_string(os.environ["COSMOS_CONNECTION_STRING"])
    container = cosmos.get_database_client("psr").get_container_client("sermons")

    try:
        doc = container.read_item(sermon_id, partition_key=sermon_id)
    except exceptions.CosmosResourceNotFoundError:
        return _json_response({"error": "Sermon not found"}, 404)

    for key in ("_rid", "_self", "_etag", "_attachments", "_ts", "uploaderIp", "uploadedAt"):
        doc.pop(key, None)

    if not include_transcript:
        transcript = doc.get("transcript")
        if transcript:
            doc["transcript"] = {
                "wordCount": len((transcript.get("fullText") or "").split()),
            }
        doc.pop("translations", None)

    cache = {"Cache-Control": "public, max-age=300"} if doc.get("status") == "complete" else {}
    return _json_response(doc, headers=cache)


@bp.route(route="sermons/{sermon_id}/transcript", methods=["GET"])
@bp.function_name("get_sermon_transcript")
async def get_sermon_transcript(req: func.HttpRequest) -> func.HttpResponse:
    """GET /api/sermons/{id}/transcript — Full transcript text (lazy loaded by frontend)."""
    from azure.cosmos import CosmosClient, exceptions

    sermon_id = req.route_params.get("sermon_id")
    cosmos = CosmosClient.from_connection_string(os.environ["COSMOS_CONNECTION_STRING"])
    container = cosmos.get_database_client("psr").get_container_client("sermons")

    try:
        doc = container.read_item(sermon_id, partition_key=sermon_id)
    except exceptions.CosmosResourceNotFoundError:
        return _json_response({"error": "Sermon not found"}, 404)

    transcript = doc.get("transcript", {})
    translations = doc.get("translations", {})

    return _json_response({
        "fullText": transcript.get("fullText", ""),
        "segments": transcript.get("segments"),
        "translations": translations,
    }, headers={"Cache-Control": "public, max-age=3600"})


@bp.route(route="sermons/{sermon_id}/translate", methods=["POST"])
@bp.function_name("translate_sermon")
async def translate_sermon(req: func.HttpRequest) -> func.HttpResponse:
    """POST /api/sermons/{id}/translate — Translate transcript via Azure Translator."""
    import requests as http_requests
    from azure.cosmos import CosmosClient, exceptions

    sermon_id = req.route_params.get("sermon_id")
    try:
        body = req.get_json()
    except Exception:
        return _json_response({"error": "Invalid JSON"}, 400)

    target_lang = body.get("language", "es")

    cosmos = CosmosClient.from_connection_string(os.environ["COSMOS_CONNECTION_STRING"])
    container = cosmos.get_database_client("psr").get_container_client("sermons")

    try:
        doc = container.read_item(sermon_id, partition_key=sermon_id)
    except exceptions.CosmosResourceNotFoundError:
        return _json_response({"error": "Sermon not found"}, 404)

    cached = doc.get("translations", {}).get(target_lang)
    if cached:
        return _json_response({"language": target_lang, "text": cached})

    text = doc.get("transcript", {}).get("fullText", "")
    if not text:
        return _json_response({"error": "No transcript available"}, 400)

    key = os.environ.get("TRANSLATOR_KEY", "")
    region = os.environ.get("TRANSLATOR_REGION", "eastus2")
    if not key:
        return _json_response({"error": "Translation service not configured"}, 500)

    chunks = [text[i:i+5000] for i in range(0, len(text), 5000)]
    translated_parts = []
    for chunk in chunks:
        for attempt in range(3):
            resp = http_requests.post(
                "https://api.cognitive.microsofttranslator.com/translate",
                params={"api-version": "3.0", "to": target_lang},
                headers={"Ocp-Apim-Subscription-Key": key, "Ocp-Apim-Subscription-Region": region, "Content-Type": "application/json"},
                json=[{"Text": chunk}],
                timeout=30,
            )
            if resp.status_code == 200:
                translated_parts.append(resp.json()[0]["translations"][0]["text"])
                break
            elif resp.status_code == 429:
                import time
                time.sleep(2 * (attempt + 1))
            else:
                log.error(f"[translate] Azure Translator error: {resp.status_code} {resp.text}")
                return _json_response({"error": "Translation failed"}, 500)
        else:
            return _json_response({"error": "Translation rate limited. Try again in a moment."}, 429)

    translated = "".join(translated_parts)

    translations = doc.get("translations", {})
    translations[target_lang] = translated
    doc["translations"] = translations
    container.upsert_item(doc)

    return _json_response({"language": target_lang, "text": translated})


@bp.route(route="sermons/{sermon_id}/bonus", methods=["PATCH"])
@bp.function_name("apply_bonus")
async def apply_bonus(req: func.HttpRequest) -> func.HttpResponse:
    """PATCH /api/sermons/{id}/bonus — Apply bonus points (admin only)."""
    from azure.cosmos import CosmosClient, exceptions

    auth_err = _require_admin(req)
    if auth_err:
        return auth_err

    sermon_id = req.route_params.get("sermon_id")
    try:
        body = req.get_json()
    except Exception:
        return _json_response({"error": "Invalid JSON"}, 400)

    bonus = body.get("bonus")
    if bonus is None or not isinstance(bonus, (int, float)) or abs(bonus) > 50:
        return _json_response({"error": "bonus must be a number between -50 and 50"}, 400)

    cosmos = CosmosClient.from_connection_string(os.environ["COSMOS_CONNECTION_STRING"])
    container = cosmos.get_database_client("psr").get_container_client("sermons")

    try:
        doc = container.read_item(sermon_id, partition_key=sermon_id)
    except exceptions.CosmosResourceNotFoundError:
        return _json_response({"error": "Sermon not found"}, 404)

    if doc.get("status") != "complete":
        return _json_response({"error": "Sermon not yet scored"}, 400)

    bonus = round(bonus, 1)
    psr = doc["compositePsr"]
    total = round(min(100, max(0, psr + bonus)), 1)

    doc["bonus"] = bonus
    doc["bonusReason"] = body.get("reason", "")
    doc["bonusRows"] = body.get("bonusRows")
    doc["totalScore"] = total
    container.upsert_item(doc)

    log.info(f"[apply_bonus] {sermon_id}: PSR={psr}, bonus={bonus}, total={total}")
    return _json_response({"id": sermon_id, "compositePsr": psr, "bonus": bonus, "totalScore": total})


@bp.route(route="sermons/{sermon_id}", methods=["DELETE"])
@bp.function_name("delete_sermon")
async def delete_sermon(req: func.HttpRequest) -> func.HttpResponse:
    """DELETE /api/sermons/{id} — Delete a sermon and its blob (admin only)."""
    from azure.cosmos import CosmosClient, exceptions
    from azure.storage.blob import ContainerClient

    auth_err = _require_admin(req)
    if auth_err:
        return auth_err

    sermon_id = req.route_params.get("sermon_id")
    cosmos = CosmosClient.from_connection_string(os.environ["COSMOS_CONNECTION_STRING"])
    container = cosmos.get_database_client("psr").get_container_client("sermons")

    try:
        doc = container.read_item(sermon_id, partition_key=sermon_id)
    except exceptions.CosmosResourceNotFoundError:
        return _json_response({"error": "Sermon not found"}, 404)

    try:
        blob_container = ContainerClient.from_connection_string(
            os.environ["STORAGE_CONNECTION_STRING"], "sermon-audio"
        )
        blobs = blob_container.list_blobs(name_starts_with=f"{sermon_id}/")
        for blob in blobs:
            blob_container.delete_blob(blob.name)
    except Exception as e:
        log.warning(f"[delete_sermon] Blob cleanup failed for {sermon_id}: {e}")

    container.delete_item(sermon_id, partition_key=sermon_id)
    log.info(f"[delete_sermon] Deleted {sermon_id}: {doc.get('title')}")
    return _json_response({"deleted": sermon_id})


@bp.route(route="sermons/{sermon_id}", methods=["PATCH"])
@bp.function_name("edit_sermon")
async def edit_sermon(req: func.HttpRequest) -> func.HttpResponse:
    """PATCH /api/sermons/{id} — Edit sermon metadata (admin only)."""
    from azure.cosmos import CosmosClient, exceptions

    auth_err = _require_admin(req)
    if auth_err:
        return auth_err

    sermon_id = req.route_params.get("sermon_id")
    try:
        body = req.get_json()
    except Exception:
        return _json_response({"error": "Invalid JSON"}, 400)

    EDITABLE = {"title", "pastor", "date", "sermonType", "churchId"}
    updates = {k: v for k, v in body.items() if k in EDITABLE and v is not None}
    if not updates:
        return _json_response({"error": "No valid fields to update"}, 400)

    cosmos = CosmosClient.from_connection_string(os.environ["COSMOS_CONNECTION_STRING"])
    container = cosmos.get_database_client("psr").get_container_client("sermons")

    try:
        doc = container.read_item(sermon_id, partition_key=sermon_id)
    except exceptions.CosmosResourceNotFoundError:
        return _json_response({"error": "Sermon not found"}, 404)

    for k, v in updates.items():
        doc[k] = v
    container.upsert_item(doc)

    log.info(f"[edit_sermon] {sermon_id}: updated {list(updates.keys())}")
    return _json_response({k: doc.get(k) for k in ["id", "title", "pastor", "date", "sermonType"]})
