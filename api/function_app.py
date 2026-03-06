"""PSR Function App — API endpoints + Durable Functions orchestrator."""

import json
import logging
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


@app.route(route="sermons", methods=["GET"])
@app.function_name("list_sermons")
async def list_sermons(req: func.HttpRequest) -> func.HttpResponse:
    """GET /api/sermons — Feed list."""
    import os
    from azure.cosmos import CosmosClient

    cosmos = CosmosClient.from_connection_string(os.environ["COSMOS_CONNECTION_STRING"])
    container = cosmos.get_database_client("psr").get_container_client("sermons")

    query = "SELECT c.id, c.title, c.pastor, c.date, c.duration, c.status, c.sermonType, c.compositePsr FROM c ORDER BY c.date DESC"
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

        # ── Normalize + composite ──
        _set_status(context, sermon_id, "finalizing")

        raw_scores = {**pass1, **pass2, **pass3}
        sermon_type = classification["sermonType"]
        confidence = classification["confidence"]

        categories, norm_applied = normalize_scores(raw_scores, sermon_type, confidence)
        composite = compute_composite(categories)

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
            "audioMetrics": audio_metrics,
            "wpmFlag": wpm_flag,
        }

        yield context.call_activity_with_retry("activity_update_sermon", RETRY_LIGHT, {
            "sermonId": sermon_id,
            "updates": updates,
        })

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


# ─────────────────────────────────────────────
#  Activity Function Registrations (with logging)
# ─────────────────────────────────────────────

from activities import (
    transcribe, analyze_audio, pass1_biblical, pass2_structure,
    pass3_delivery, classify_sermon, classify_segments,
    generate_summary, update_sermon,
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


app.register_functions(bp)
