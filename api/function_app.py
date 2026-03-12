"""PSR Function App — API endpoints + Durable Functions orchestrator."""

import json
import logging
import os
import time
import uuid

import azure.functions as func
import azure.durable_functions as df

from schema import (
    new_sermon_doc,
    normalize_scores,
    compute_composite,
    fail_sermon_doc,
    CATEGORY_WEIGHTS,
    PIPELINE_VERSION,
    SCORING_MODELS,
    PASS_HASHES,
)

app = func.FunctionApp(http_auth_level=func.AuthLevel.ANONYMOUS)
bp = df.Blueprint()

log = logging.getLogger(__name__)

ALLOWED_TYPES = {
    "audio/mpeg": ".mp3",
    "audio/wav": ".wav",
    "audio/x-wav": ".wav",
    "audio/wave": ".wav",
    "audio/mp4": ".m4a",
    "audio/x-m4a": ".m4a",
}
MAX_SIZE = 100 * 1024 * 1024  # 100MB


# ─────────────────────────────────────────────
#  HTTP Triggers
# ─────────────────────────────────────────────


@app.route(route="sermons", methods=["POST"])
@app.durable_client_input(client_name="starter")
@app.function_name("upload_sermon")
async def upload_sermon(req: func.HttpRequest, starter: df.DurableOrchestrationClient) -> func.HttpResponse:
    """POST /api/sermons — Upload audio and start processing."""
    import os
    import datetime
    from azure.cosmos import CosmosClient
    from azure.storage.blob import BlobClient

    # ── Guard 1: Content-Length pre-check (reject before buffering) ──
    content_length = req.headers.get("Content-Length")
    if content_length and int(content_length) > MAX_SIZE:
        return _json_response({"error": "File too large. Max 100MB."}, 413)

    cosmos = CosmosClient.from_connection_string(os.environ["COSMOS_CONNECTION_STRING"])
    container = cosmos.get_database_client("psr").get_container_client("sermons")

    # ── Guard 2: Concurrency gate (max 3 processing at once) ──
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

    # ── Guard 3: Rate limit (5 uploads per IP per hour) ──
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

    # Validate file
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

    # Store audio in Blob Storage
    try:
        blob = BlobClient.from_connection_string(
            os.environ["STORAGE_CONNECTION_STRING"], "sermon-audio", blob_name
        )
        blob.upload_blob(audio_bytes, content_type=content_type)
    except Exception as e:
        log.error(f"[upload] Blob upload failed for {sermon_id}: {e}", exc_info=True)
        return _json_response({"error": "Failed to store audio file. Please retry."}, 500)

    # Create Cosmos DB record (includes IP + timestamp for rate limiting)
    doc = new_sermon_doc(sermon_id, filename, title, pastor)
    doc["blobUrl"] = blob_name
    doc["uploaderIp"] = client_ip
    doc["uploadedAt"] = datetime.datetime.utcnow().isoformat() + "Z"
    try:
        container.create_item(doc)
    except Exception as e:
        log.error(f"[upload] Cosmos create failed for {sermon_id}: {e}", exc_info=True)
        return _json_response({"error": "Failed to create sermon record. Please retry."}, 500)

    # Start Durable Functions orchestrator
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
        # Mark sermon as failed so it doesn't sit at "processing" forever
        try:
            container.upsert_item({**doc, **fail_sermon_doc("Orchestrator failed to start — please re-upload")})
        except Exception:
            pass
        return _json_response({"error": "Processing failed to start. Please retry."}, 500)

    return _json_response({"id": sermon_id, "status": "processing"}, 202)


ALLOWED_TEXT_TYPES = {
    "text/plain": ".txt",
    "text/markdown": ".md",
    "text/html": ".html",
    "text/csv": ".csv",
    "text/rtf": ".rtf",
    "text/xml": ".xml",
    "application/rtf": ".rtf",
    "application/pdf": ".pdf",
    "application/msword": ".doc",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": ".docx",
    "application/vnd.oasis.opendocument.text": ".odt",
}
ALLOWED_TEXT_EXTENSIONS = {".txt", ".md", ".html", ".htm", ".csv", ".rtf", ".xml", ".pdf", ".doc", ".docx", ".odt"}
MAX_TEXT_SIZE = 10 * 1024 * 1024  # 10MB


def _extract_text(file_bytes, filename, content_type):
    """Extract plain text from uploaded file. Returns str or raises ValueError."""
    ext = os.path.splitext(filename)[1].lower() if filename else ""

    # Plain text formats — decode directly
    if ext in {".txt", ".md", ".csv", ".xml", ".html", ".htm"} or content_type in {"text/plain", "text/markdown", "text/csv", "text/xml", "text/html"}:
        for enc in ("utf-8", "utf-8-sig", "latin-1"):
            try:
                return file_bytes.decode(enc)
            except (UnicodeDecodeError, ValueError):
                continue
        raise ValueError("Could not decode text file")

    # DOCX
    if ext == ".docx" or content_type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
        import zipfile, io, xml.etree.ElementTree as ET
        with zipfile.ZipFile(io.BytesIO(file_bytes)) as z:
            xml_content = z.read("word/document.xml")
        root = ET.fromstring(xml_content)
        ns = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
        return "\n".join(p.text for p in root.iter(f"{{{ns['w']}}}t") if p.text)

    # PDF
    if ext == ".pdf" or content_type == "application/pdf":
        raise ValueError("PDF upload not yet supported — please copy/paste the text into a .txt file")

    # DOC (legacy binary)
    if ext == ".doc" or content_type == "application/msword":
        raise ValueError(".doc format not supported — please save as .docx or .txt")

    # RTF
    if ext == ".rtf" or content_type in {"text/rtf", "application/rtf"}:
        # Strip RTF control words for basic extraction
        import re
        text = file_bytes.decode("latin-1")
        text = re.sub(r'\\[a-z]+\d*\s?', '', text)
        text = re.sub(r'[{}]', '', text)
        return text.strip()

    # ODT
    if ext == ".odt" or content_type == "application/vnd.oasis.opendocument.text":
        import zipfile, io, xml.etree.ElementTree as ET
        with zipfile.ZipFile(io.BytesIO(file_bytes)) as z:
            xml_content = z.read("content.xml")
        root = ET.fromstring(xml_content)
        ns = {"text": "urn:oasis:names:tc:opendocument:xmlns:text:1.0"}
        return "\n".join("".join(p.itertext()) for p in root.iter(f"{{{ns['text']}}}p"))

    raise ValueError(f"Unsupported file type: {ext or content_type}")


@app.route(route="sermons/text", methods=["POST"])
@app.durable_client_input(client_name="starter")
@app.function_name("upload_text_sermon")
async def upload_text_sermon(req: func.HttpRequest, starter: df.DurableOrchestrationClient) -> func.HttpResponse:
    """POST /api/sermons/text — Upload text transcript and start processing (skip transcription + audio)."""
    import os
    import datetime
    from azure.cosmos import CosmosClient

    cosmos = CosmosClient.from_connection_string(os.environ["COSMOS_CONNECTION_STRING"])
    container = cosmos.get_database_client("psr").get_container_client("sermons")

    # ── Concurrency gate ──
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

    # ── Rate limit ──
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

    # ── Validate file ──
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

    # ── Extract text ──
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

    # ── Create Cosmos DB record ──
    doc = new_sermon_doc(sermon_id, filename, title, pastor)
    doc["uploaderIp"] = client_ip
    doc["uploadedAt"] = datetime.datetime.utcnow().isoformat() + "Z"
    doc["inputType"] = "text"
    try:
        container.create_item(doc)
    except Exception as e:
        log.error(f"[upload_text] Cosmos create failed for {sermon_id}: {e}", exc_info=True)
        return _json_response({"error": "Failed to create sermon record. Please retry."}, 500)

    # ── Start text orchestrator ──
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


def _extract_video_id(url):
    """Extract YouTube video ID from various URL formats."""
    import re
    patterns = [
        r'(?:youtube\.com/watch\?v=|youtu\.be/|youtube\.com/embed/|youtube\.com/v/)([a-zA-Z0-9_-]{11})',
        r'^([a-zA-Z0-9_-]{11})$',
    ]
    for p in patterns:
        m = re.search(p, url.strip())
        if m:
            return m.group(1)
    return None


def _parse_timestamp(ts):
    """Parse H:MM:SS or MM:SS or SS into seconds. Returns None on failure."""
    if not ts or not ts.strip():
        return None
    parts = ts.strip().split(":")
    try:
        parts = [int(p) for p in parts]
    except ValueError:
        return None
    if len(parts) == 3:
        return parts[0] * 3600 + parts[1] * 60 + parts[2]
    if len(parts) == 2:
        return parts[0] * 60 + parts[1]
    if len(parts) == 1:
        return parts[0]
    return None


@app.route(route="sermons/youtube", methods=["POST"])
@app.durable_client_input(client_name="starter")
@app.function_name("upload_youtube_sermon")
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

    # ── Concurrency gate ──
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

    # ── Rate limit ──
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

    # ── Fetch YouTube transcript ──
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

        fetched = ytt.fetch(video_id, languages=["en"])
        # Filter to requested time range
        filtered = [s for s in fetched if s.start >= start_sec and s.start < end_sec]
        if not filtered:
            return _json_response({"error": f"No transcript found between {body.get('start')} and {body.get('end')}. Check your timestamps."}, 400)
        transcript_text = " ".join(s.text for s in filtered)
    except Exception as e:
        err_str = str(e)
        log.warning(f"[upload_youtube] Failed to fetch transcript for {video_id}: {e}")
        if "blocking" in err_str.lower() or "ip" in err_str.lower() or "RequestBlocked" in err_str or "IpBlocked" in err_str:
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

    # ── Create Cosmos DB record ──
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

    # ── Start text orchestrator (same as text upload — no audio) ──
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


@app.route(route="sermons", methods=["GET"])
@app.function_name("list_sermons")
async def list_sermons(req: func.HttpRequest) -> func.HttpResponse:
    """GET /api/sermons — Feed list."""
    import os
    from azure.cosmos import CosmosClient

    cosmos = CosmosClient.from_connection_string(os.environ["COSMOS_CONNECTION_STRING"])
    container = cosmos.get_database_client("psr").get_container_client("sermons")

    query = "SELECT c.id, c.title, c.pastor, c.date, c.duration, c.status, c.sermonType, c.compositePsr, c.inputType, c.bonus, c.totalScore FROM c ORDER BY c.date DESC"
    items = list(container.query_items(query, enable_cross_partition_query=True))

    return _json_response(items)


@app.route(route="sermons/{sermon_id}", methods=["GET"])
@app.function_name("get_sermon")
async def get_sermon(req: func.HttpRequest) -> func.HttpResponse:
    """GET /api/sermons/{id} — Full sermon detail."""
    import os
    from azure.cosmos import CosmosClient, exceptions

    sermon_id = req.route_params.get("sermon_id")
    cosmos = CosmosClient.from_connection_string(os.environ["COSMOS_CONNECTION_STRING"])
    container = cosmos.get_database_client("psr").get_container_client("sermons")

    try:
        doc = container.read_item(sermon_id, partition_key=sermon_id)
    except exceptions.CosmosResourceNotFoundError:
        return _json_response({"error": "Sermon not found"}, 404)

    # Strip Cosmos metadata + internal fields
    for key in ("_rid", "_self", "_etag", "_attachments", "_ts", "uploaderIp", "uploadedAt"):
        doc.pop(key, None)

    return _json_response(doc)


@app.route(route="sermons/{sermon_id}/translate", methods=["POST"])
@app.function_name("translate_sermon")
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

    # Check cache
    cached = doc.get("translations", {}).get(target_lang)
    if cached:
        return _json_response({"language": target_lang, "text": cached})

    text = doc.get("transcript", {}).get("fullText", "")
    if not text:
        return _json_response({"error": "No transcript available"}, 400)

    # Azure Translator API — split into chunks of 5000 chars (API limit)
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

    # Cache in Cosmos
    translations = doc.get("translations", {})
    translations[target_lang] = translated
    doc["translations"] = translations
    container.upsert_item(doc)

    return _json_response({"language": target_lang, "text": translated})


@app.route(route="sermons/{sermon_id}/bonus", methods=["PATCH"])
@app.function_name("apply_bonus")
async def apply_bonus(req: func.HttpRequest) -> func.HttpResponse:
    """PATCH /api/sermons/{id}/bonus — Apply bonus points (admin only)."""
    import os
    from azure.cosmos import CosmosClient, exceptions

    admin_key = os.environ.get("ADMIN_KEY", "")
    provided = req.headers.get("x-admin-key", "")
    if not admin_key or provided != admin_key:
        return _json_response({"error": "Unauthorized"}, 401)

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


@app.route(route="sermons/{sermon_id}", methods=["DELETE"])
@app.function_name("delete_sermon")
async def delete_sermon(req: func.HttpRequest) -> func.HttpResponse:
    """DELETE /api/sermons/{id} — Delete a sermon and its blob (admin only)."""
    import os
    from azure.cosmos import CosmosClient, exceptions
    from azure.storage.blob import ContainerClient

    admin_key = os.environ.get("ADMIN_KEY", "")
    provided = req.headers.get("x-admin-key", "")
    if not admin_key or provided != admin_key:
        return _json_response({"error": "Unauthorized"}, 401)

    sermon_id = req.route_params.get("sermon_id")
    cosmos = CosmosClient.from_connection_string(os.environ["COSMOS_CONNECTION_STRING"])
    container = cosmos.get_database_client("psr").get_container_client("sermons")

    try:
        doc = container.read_item(sermon_id, partition_key=sermon_id)
    except exceptions.CosmosResourceNotFoundError:
        return _json_response({"error": "Sermon not found"}, 404)

    # Delete blob folder (best-effort)
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


@app.route(route="sermons/{sermon_id}", methods=["PATCH"])
@app.function_name("edit_sermon")
async def edit_sermon(req: func.HttpRequest) -> func.HttpResponse:
    """PATCH /api/sermons/{id} — Edit sermon metadata (admin only)."""
    import os
    from azure.cosmos import CosmosClient, exceptions

    admin_key = os.environ.get("ADMIN_KEY", "")
    provided = req.headers.get("x-admin-key", "")
    if not admin_key or provided != admin_key:
        return _json_response({"error": "Unauthorized"}, 401)

    sermon_id = req.route_params.get("sermon_id")
    try:
        body = req.get_json()
    except Exception:
        return _json_response({"error": "Invalid JSON"}, 400)

    EDITABLE = {"title", "pastor", "date", "sermonType"}
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


@app.route(route="churches", methods=["GET"])
@app.function_name("list_churches")
async def list_churches(req: func.HttpRequest) -> func.HttpResponse:
    """GET /api/churches — List all churches with pastors and sermon stats."""
    import os
    from azure.cosmos import CosmosClient

    cosmos = CosmosClient.from_connection_string(os.environ["COSMOS_CONNECTION_STRING"])
    db = cosmos.get_database_client("psr")

    # Get churches from dedicated container (create if missing)
    try:
        church_container = db.get_container_client("churches")
        churches = list(church_container.query_items(
            "SELECT * FROM c", enable_cross_partition_query=True
        ))
    except Exception:
        churches = []

    # Strip Cosmos metadata
    for c in churches:
        for key in ("_rid", "_self", "_etag", "_attachments", "_ts"):
            c.pop(key, None)

    # Enrich with sermon stats per pastor
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


@app.route(route="churches", methods=["POST"])
@app.function_name("upsert_church")
async def upsert_church(req: func.HttpRequest) -> func.HttpResponse:
    """POST /api/churches — Create or update a church (admin only)."""
    import os
    from azure.cosmos import CosmosClient

    admin_key = os.environ.get("ADMIN_KEY", "")
    provided = req.headers.get("x-admin-key", "")
    if not admin_key or provided != admin_key:
        return _json_response({"error": "Unauthorized"}, 401)

    try:
        body = req.get_json()
    except Exception:
        return _json_response({"error": "Invalid JSON"}, 400)

    required = ["id", "name", "city", "state"]
    if not all(body.get(k) for k in required):
        return _json_response({"error": f"Required fields: {required}"}, 400)

    cosmos = CosmosClient.from_connection_string(os.environ["COSMOS_CONNECTION_STRING"])
    db = cosmos.get_database_client("psr")

    # Ensure churches container exists
    try:
        church_container = db.create_container_if_not_exists(id="churches", partition_key={"paths": ["/id"], "kind": "Hash"})
    except Exception:
        church_container = db.get_container_client("churches")

    church_container.upsert_item(body)
    log.info(f"[upsert_church] {body['id']}: {body['name']}")
    return _json_response(body)


@app.route(route="churches/{church_id}", methods=["DELETE"])
@app.function_name("delete_church")
async def delete_church(req: func.HttpRequest) -> func.HttpResponse:
    """DELETE /api/churches/{id} — Remove a church (admin only)."""
    import os
    from azure.cosmos import CosmosClient, exceptions

    admin_key = os.environ.get("ADMIN_KEY", "")
    provided = req.headers.get("x-admin-key", "")
    if not admin_key or provided != admin_key:
        return _json_response({"error": "Unauthorized"}, 401)

    church_id = req.route_params.get("church_id")
    cosmos = CosmosClient.from_connection_string(os.environ["COSMOS_CONNECTION_STRING"])
    try:
        container = cosmos.get_database_client("psr").get_container_client("churches")
        container.delete_item(church_id, partition_key=church_id)
    except exceptions.CosmosResourceNotFoundError:
        return _json_response({"error": "Church not found"}, 404)

    log.info(f"[delete_church] {church_id}")
    return _json_response({"deleted": church_id})


def _json_response(body, status=200):
    return func.HttpResponse(
        json.dumps(body, default=str),
        status_code=status,
        mimetype="application/json",
    )


# ─────────────────────────────────────────────
#  Durable Functions Orchestrator
# ─────────────────────────────────────────────

RETRY_LLM = df.RetryOptions(
    first_retry_interval_in_milliseconds=60_000,  # 60s (POC #8: 429s need 60-180s)
    max_number_of_attempts=4,
)
RETRY_TRANSCRIBE = df.RetryOptions(
    first_retry_interval_in_milliseconds=30_000,
    max_number_of_attempts=3,
)
RETRY_LIGHT = df.RetryOptions(
    first_retry_interval_in_milliseconds=10_000,
    max_number_of_attempts=2,
)


def _set_status(context, sermon_id, step):
    """Set custom status + log (only on non-replay to avoid noise)."""
    context.set_custom_status({"step": step, "sermonId": sermon_id})
    if not context.is_replaying:
        log.info(f"[orchestrator] {sermon_id}: {step}")


@bp.orchestration_trigger(context_name="context")
def sermon_orchestrator(context: df.DurableOrchestrationContext):
    """Main pipeline: transcribe → score → store."""
    input_data = context.get_input()
    sermon_id = input_data["sermonId"]
    blob_url = input_data["blobUrl"]

    try:
        # ── Wave 1: Transcribe + Parselmouth in parallel ──
        _set_status(context, sermon_id, "transcribing")

        transcribe_task = context.call_activity_with_retry(
            "activity_transcribe", RETRY_TRANSCRIBE,
            {"blobUrl": blob_url, "sermonId": sermon_id},
        )
        audio_task = context.call_activity_with_retry(
            "activity_analyze_audio", RETRY_LIGHT,
            {"blobUrl": blob_url},
        )

        transcript_result = yield transcribe_task

        # Audio analysis: graceful degradation if it fails
        try:
            audio_metrics = yield audio_task
        except Exception as e:
            audio_metrics = None
            if not context.is_replaying:
                log.warning(f"[orchestrator] {sermon_id}: Parselmouth failed ({e}), proceeding without audio")

        transcript_text = transcript_result["fullText"]
        wpm = transcript_result["wpm"]
        wpm_flag = wpm < 80 or wpm > 200

        if not context.is_replaying:
            log.info(f"[orchestrator] {sermon_id}: transcribed {transcript_result['wordCount']} words, {wpm} WPM")

        # ── Wave 2: 5 LLM passes in parallel ──
        _set_status(context, sermon_id, "scoring")

        pass1_task = context.call_activity_with_retry(
            "activity_pass1_biblical", RETRY_LLM,
            {"transcript": transcript_text},
        )
        pass2_task = context.call_activity_with_retry(
            "activity_pass2_structure", RETRY_LLM,
            {"transcript": transcript_text},
        )
        pass3_task = context.call_activity_with_retry(
            "activity_pass3_delivery", RETRY_LLM,
            {
                "transcript": transcript_text,
                "audioMetrics": audio_metrics or _default_audio_metrics(),
                "wpm": wpm,
                "audioAvailable": audio_metrics is not None,
            },
        )
        classify_task = context.call_activity_with_retry(
            "activity_classify_sermon", RETRY_LLM,
            {
                "transcript": transcript_text,
                "userTitle": input_data.get("userTitle"),
                "userPastor": input_data.get("userPastor"),
            },
        )
        segment_task = context.call_activity_with_retry(
            "activity_classify_segments", RETRY_LIGHT,
            {"segments": transcript_result["segments"]},
        )

        pass4_task = context.call_activity_with_retry(
            "activity_pass4_enrichment", RETRY_LLM,
            {"transcript": transcript_text},
        )

        # Fan-in
        pass1 = yield pass1_task
        pass2 = yield pass2_task
        pass3 = yield pass3_task
        classification = yield classify_task

        try:
            classified_segments = yield segment_task
        except Exception as e:
            classified_segments = transcript_result["segments"]
            if not context.is_replaying:
                log.warning(f"[orchestrator] {sermon_id}: segment classification failed ({e}), using defaults")

        try:
            enrichment_result = yield pass4_task
            enrichment = enrichment_result.get("enrichment")
        except Exception as e:
            enrichment = None
            if not context.is_replaying:
                log.warning(f"[orchestrator] {sermon_id}: pass4 enrichment failed ({e}), skipping")

        # ── Normalize + composite ──
        _set_status(context, sermon_id, "finalizing")

        raw_scores = {**pass1, **pass2, **pass3}
        sermon_type = classification["sermonType"]
        confidence = classification["confidence"]

        categories, norm_applied = normalize_scores(raw_scores, sermon_type, confidence)
        composite = compute_composite(categories)

        # Preserve raw (pre-normalization) scores for future recalibration
        raw_score_map = {k: raw_scores[k]["score"] for k in raw_scores}

        if not context.is_replaying:
            log.info(f"[orchestrator] {sermon_id}: PSR={composite}, type={sermon_type} ({confidence}%)")

        # ── Generate summary ──
        summary_result = yield context.call_activity_with_retry(
            "activity_generate_summary", RETRY_LIGHT,
            {"categories": categories, "sermonType": sermon_type},
        )

        # ── Store results ──
        duration_seconds = round(transcript_result["durationMs"] / 1000)
        updates = {
            "status": "complete",
            "title": classification["title"],
            "pastor": classification["pastor"],
            "duration": duration_seconds,
            "sermonType": sermon_type,
            "compositePsr": composite,
            "summary": summary_result.get("summary"),
            "categories": categories,
            "strengths": summary_result.get("strengths"),
            "improvements": summary_result.get("improvements"),
            "transcript": {
                "fullText": transcript_text,
                "segments": classified_segments,
            },
            "classificationConfidence": confidence,
            "normalizationApplied": norm_applied,
            "rawScores": raw_score_map,
            "audioMetrics": audio_metrics,
            "wpmFlag": wpm_flag,
            "enrichment": enrichment,
            "pipelineVersion": PIPELINE_VERSION,
            "scoringModels": SCORING_MODELS,
            "passVersions": PASS_HASHES,
        }

        yield context.call_activity_with_retry("activity_update_sermon", RETRY_LIGHT, {
            "sermonId": sermon_id,
            "updates": updates,
        })

        # Auto-create church if pastor is new
        try:
            yield context.call_activity_with_retry("activity_ensure_church", RETRY_LIGHT, {
                "pastor": classification["pastor"],
            })
        except Exception as e:
            if not context.is_replaying:
                log.warning(f"[orchestrator] {sermon_id}: ensure_church failed ({e}), non-fatal")

        _set_status(context, sermon_id, "complete")

    except Exception as e:
        if not context.is_replaying:
            log.error(f"[orchestrator] {sermon_id}: pipeline failed: {e}", exc_info=True)
        _set_status(context, sermon_id, "failed")
        try:
            yield context.call_activity_with_retry("activity_update_sermon", RETRY_LIGHT, {
                "sermonId": sermon_id,
                "updates": fail_sermon_doc(str(e)),
            })
        except Exception as update_err:
            # Last resort: log the double failure so it's findable in App Insights
            if not context.is_replaying:
                log.critical(
                    f"[orchestrator] {sermon_id}: DOUBLE FAULT — pipeline failed ({e}) "
                    f"AND error recording failed ({update_err}). Sermon stuck at 'processing'."
                )


def _default_audio_metrics():
    """Fallback when Parselmouth fails — lets delivery pass still run."""
    return {
        "pitchMeanHz": 0, "pitchStdHz": 0, "pitchRangeHz": 0,
        "intensityMeanDb": 0, "intensityRangeDb": 0, "noiseFloorDb": 0,
        "pauseCount": 0, "pausesPerMinute": 0, "durationSeconds": 0,
    }


@bp.orchestration_trigger(context_name="context")
def text_sermon_orchestrator(context: df.DurableOrchestrationContext):
    """Pipeline for text-only sermons: skip transcription + Parselmouth, go straight to scoring."""
    input_data = context.get_input()
    sermon_id = input_data["sermonId"]
    transcript_text = input_data["transcript"]
    word_count = input_data["wordCount"]

    try:
        # Estimate WPM assuming ~140 WPM average speaking rate
        estimated_duration = word_count / 140 * 60  # seconds
        wpm = 140.0

        # ── Build segments from paragraphs (split large blocks into ~100-word chunks) ──
        paragraphs = [p.strip() for p in transcript_text.split("\n") if p.strip()]
        # If text has very few paragraphs, split into sentence-based chunks
        if len(paragraphs) <= 3 and word_count > 200:
            import re
            sentences = re.split(r'(?<=[.!?])\s+', transcript_text.strip())
            chunks, current = [], []
            wc = 0
            for s in sentences:
                current.append(s)
                wc += len(s.split())
                if wc >= 100:
                    chunks.append(" ".join(current))
                    current, wc = [], 0
            if current:
                chunks.append(" ".join(current))
            paragraphs = chunks if len(chunks) > 3 else paragraphs
        seg_duration = estimated_duration / max(len(paragraphs), 1)
        segments = []
        for i, para in enumerate(paragraphs):
            segments.append({
                "start": round(i * seg_duration, 2),
                "end": round((i + 1) * seg_duration, 2),
                "text": para,
                "type": "teaching",
            })

        # ── LLM passes in parallel (no audio) ──
        _set_status(context, sermon_id, "scoring")

        pass1_task = context.call_activity_with_retry(
            "activity_pass1_biblical", RETRY_LLM, {"transcript": transcript_text},
        )
        pass2_task = context.call_activity_with_retry(
            "activity_pass2_structure", RETRY_LLM, {"transcript": transcript_text},
        )
        pass3_task = context.call_activity_with_retry(
            "activity_pass3_delivery", RETRY_LLM,
            {
                "transcript": transcript_text,
                "audioMetrics": _default_audio_metrics(),
                "wpm": wpm,
                "audioAvailable": False,
            },
        )
        classify_task = context.call_activity_with_retry(
            "activity_classify_sermon", RETRY_LLM,
            {
                "transcript": transcript_text,
                "userTitle": input_data.get("userTitle"),
                "userPastor": input_data.get("userPastor"),
            },
        )
        segment_task = context.call_activity_with_retry(
            "activity_classify_segments", RETRY_LIGHT, {"segments": segments},
        )

        pass4_task = context.call_activity_with_retry(
            "activity_pass4_enrichment", RETRY_LLM,
            {"transcript": transcript_text},
        )

        pass1 = yield pass1_task
        pass2 = yield pass2_task
        pass3 = yield pass3_task
        classification = yield classify_task

        try:
            classified_segments = yield segment_task
        except Exception:
            classified_segments = segments

        try:
            enrichment_result = yield pass4_task
            enrichment = enrichment_result.get("enrichment")
        except Exception:
            enrichment = None

        # ── Normalize + composite ──
        _set_status(context, sermon_id, "finalizing")

        raw_scores = {**pass1, **pass2, **pass3}
        sermon_type = classification["sermonType"]
        confidence = classification["confidence"]

        categories, norm_applied = normalize_scores(raw_scores, sermon_type, confidence, audio_available=False)
        composite = compute_composite(categories)
        raw_score_map = {k: raw_scores[k]["score"] for k in raw_scores}

        if not context.is_replaying:
            log.info(f"[text_orchestrator] {sermon_id}: PSR={composite}, type={sermon_type} ({confidence}%)")

        # ── Summary ──
        summary_result = yield context.call_activity_with_retry(
            "activity_generate_summary", RETRY_LIGHT,
            {"categories": categories, "sermonType": sermon_type},
        )

        # ── Store results ──
        updates = {
            "status": "complete",
            "title": classification["title"],
            "pastor": classification["pastor"],
            "duration": round(estimated_duration),
            "sermonType": sermon_type,
            "compositePsr": composite,
            "summary": summary_result.get("summary"),
            "categories": categories,
            "strengths": summary_result.get("strengths"),
            "improvements": summary_result.get("improvements"),
            "transcript": {
                "fullText": transcript_text,
                "segments": classified_segments,
            },
            "classificationConfidence": confidence,
            "normalizationApplied": norm_applied,
            "rawScores": raw_score_map,
            "audioMetrics": None,
            "inputType": "text",
            "wpmFlag": False,
            "enrichment": enrichment,
            "pipelineVersion": PIPELINE_VERSION,
            "scoringModels": SCORING_MODELS,
            "passVersions": PASS_HASHES,
        }

        yield context.call_activity_with_retry("activity_update_sermon", RETRY_LIGHT, {
            "sermonId": sermon_id,
            "updates": updates,
        })

        # Auto-create church if pastor is new
        try:
            yield context.call_activity_with_retry("activity_ensure_church", RETRY_LIGHT, {
                "pastor": classification["pastor"],
            })
        except Exception as e:
            if not context.is_replaying:
                log.warning(f"[text_orchestrator] {sermon_id}: ensure_church failed ({e}), non-fatal")

        _set_status(context, sermon_id, "complete")

    except Exception as e:
        if not context.is_replaying:
            log.error(f"[text_orchestrator] {sermon_id}: pipeline failed: {e}", exc_info=True)
        _set_status(context, sermon_id, "failed")
        try:
            yield context.call_activity_with_retry("activity_update_sermon", RETRY_LIGHT, {
                "sermonId": sermon_id,
                "updates": fail_sermon_doc(str(e)),
            })
        except Exception as update_err:
            if not context.is_replaying:
                log.critical(
                    f"[text_orchestrator] {sermon_id}: DOUBLE FAULT — pipeline failed ({e}) "
                    f"AND error recording failed ({update_err}). Sermon stuck at 'processing'."
                )


# ─────────────────────────────────────────────
#  Admin: Batch Rescore (function key auth)
# ─────────────────────────────────────────────

@app.route(route="rescore", methods=["POST"], auth_level=func.AuthLevel.ANONYMOUS)
@app.durable_client_input(client_name="starter")
@app.function_name("admin_rescore")
async def admin_rescore(req: func.HttpRequest, starter: df.DurableOrchestrationClient) -> func.HttpResponse:
    """POST /api/admin/rescore — Re-score sermons with current models. Requires admin key."""
    import os
    admin_key = os.environ.get("ADMIN_KEY", "")
    provided = req.headers.get("x-admin-key", "") or req.params.get("key", "")
    if not admin_key or provided != admin_key:
        return _json_response({"error": "Unauthorized"}, 401)
    body = req.get_json() if req.get_body() else {}
    sermon_ids = body.get("sermonIds")
    rescore_all = body.get("all", False)
    older_than = body.get("olderThan")  # pipeline version date string
    passes = body.get("passes")  # selective per-pass rescore: [1,2,3,4,"segments","summary","stale"]
    stale_only = body.get("staleOnly", False)  # auto-detect stale passes

    if stale_only:
        passes = ["stale"]

    if not sermon_ids and not rescore_all:
        return _json_response({"error": "Provide sermonIds array or {\"all\": true}"}, 400)

    import os
    from azure.cosmos import CosmosClient
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


@bp.orchestration_trigger(context_name="context")
def rescore_orchestrator(context: df.DurableOrchestrationContext):
    """Re-score sermons using existing transcripts. Skips transcription + Parselmouth."""
    input_data = context.get_input()
    sermon_ids = input_data["sermonIds"]
    passes = input_data.get("passes")

    results = []
    for sermon_id in sermon_ids:
        try:
            result = yield context.call_activity_with_retry(
                "activity_rescore_sermon", RETRY_LLM, {"sermonId": sermon_id, "passes": passes}
            )
            results.append({"id": sermon_id, "ok": True, "newPsr": result.get("compositePsr")})
        except Exception as e:
            results.append({"id": sermon_id, "ok": False, "error": str(e)})
            if not context.is_replaying:
                log.error(f"[rescore] {sermon_id} failed: {e}")

    context.set_custom_status({"done": True, "results": results})
    return results


# ─────────────────────────────────────────────
#  Activity Function Registrations (with logging)
# ─────────────────────────────────────────────

from activities import (
    transcribe, analyze_audio, pass1_biblical, pass2_structure,
    pass3_delivery, pass4_enrichment, classify_sermon, classify_segments,
    generate_summary, update_sermon, rescore_sermon,
)


def _run_activity(name, func, input_data):
    """Wrap activity with entry/exit logging and timing."""
    sermon_id = input_data.get("sermonId", input_data.get("blobUrl", "?"))
    log.info(f"[{name}] started | {sermon_id}")
    t0 = time.monotonic()
    try:
        result = func(input_data)
        elapsed = round(time.monotonic() - t0, 1)
        log.info(f"[{name}] completed in {elapsed}s | {sermon_id}")
        return result
    except Exception as e:
        elapsed = round(time.monotonic() - t0, 1)
        log.error(f"[{name}] failed after {elapsed}s | {sermon_id}: {e}", exc_info=True)
        raise


@bp.activity_trigger(input_name="input")
def activity_transcribe(input: dict):
    return _run_activity("transcribe", transcribe, input)

@bp.activity_trigger(input_name="input")
def activity_analyze_audio(input: dict):
    return _run_activity("analyze_audio", analyze_audio, input)

@bp.activity_trigger(input_name="input")
def activity_pass1_biblical(input: dict):
    return _run_activity("pass1_biblical", pass1_biblical, input)

@bp.activity_trigger(input_name="input")
def activity_pass2_structure(input: dict):
    return _run_activity("pass2_structure", pass2_structure, input)

@bp.activity_trigger(input_name="input")
def activity_pass3_delivery(input: dict):
    return _run_activity("pass3_delivery", pass3_delivery, input)

@bp.activity_trigger(input_name="input")
def activity_pass4_enrichment(input: dict):
    return _run_activity("pass4_enrichment", pass4_enrichment, input)

@bp.activity_trigger(input_name="input")
def activity_classify_sermon(input: dict):
    return _run_activity("classify_sermon", classify_sermon, input)

@bp.activity_trigger(input_name="input")
def activity_classify_segments(input: dict):
    return _run_activity("classify_segments", classify_segments, input)

@bp.activity_trigger(input_name="input")
def activity_generate_summary(input: dict):
    return _run_activity("generate_summary", generate_summary, input)

@bp.activity_trigger(input_name="input")
def activity_update_sermon(input: dict):
    return _run_activity("update_sermon", update_sermon, input)

@bp.activity_trigger(input_name="input")
def activity_ensure_church(input: dict):
    return _run_activity("ensure_church", ensure_church, input)

@bp.activity_trigger(input_name="input")
def activity_rescore_sermon(input: dict):
    return _run_activity("rescore_sermon", rescore_sermon, input)


app.register_functions(bp)
