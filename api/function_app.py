"""PSR Function App — API endpoints + Durable Functions orchestrator."""

import json
import logging
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
async def upload_sermon(req: func.HttpRequest, starter: str) -> func.HttpResponse:
    """POST /api/sermons — Upload audio and start processing."""
    import os
    from azure.cosmos import CosmosClient
    from azure.storage.blob import BlobClient

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
    blob = BlobClient.from_connection_string(
        os.environ["STORAGE_CONNECTION_STRING"], "sermon-audio", blob_name
    )
    blob.upload_blob(audio_bytes, content_type=content_type)

    # Create Cosmos DB record
    doc = new_sermon_doc(sermon_id, filename, title, pastor)
    doc["blobUrl"] = blob_name
    cosmos = CosmosClient.from_connection_string(os.environ["COSMOS_CONNECTION_STRING"])
    container = cosmos.get_database_client("psr").get_container_client("sermons")
    container.create_item(doc)

    # Start Durable Functions orchestrator
    client = df.DurableOrchestrationClient(starter)
    instance_id = await client.start_new("sermon_orchestrator", client_input={
        "sermonId": sermon_id,
        "blobUrl": blob_name,
        "userTitle": title,
        "userPastor": pastor,
    })
    log.info(f"Started orchestrator {instance_id} for sermon {sermon_id}")

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

    # Strip Cosmos metadata
    for key in ("_rid", "_self", "_etag", "_attachments", "_ts"):
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


@bp.orchestration_trigger(context_name="context")
def sermon_orchestrator(context: df.DurableOrchestrationContext):
    """Main pipeline: transcribe → score → store."""
    input_data = context.get_input()
    sermon_id = input_data["sermonId"]
    blob_url = input_data["blobUrl"]

    try:
        # ── Wave 1: Transcribe + Parselmouth in parallel ──
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
        except Exception:
            audio_metrics = None
            log.warning(f"Parselmouth failed for {sermon_id}, proceeding without audio metrics")

        transcript_text = transcript_result["fullText"]
        wpm = transcript_result["wpm"]

        # WPM sanity check
        wpm_flag = wpm < 80 or wpm > 200

        # ── Wave 2: 5 LLM passes in parallel ──
        pass1_task = context.call_activity_with_retry(
            "activity_pass1_biblical", RETRY_LLM,
            {"transcript": transcript_text},
        )
        pass2_task = context.call_activity_with_retry(
            "activity_pass2_structure", RETRY_LLM,
            {"transcript": transcript_text},
        )

        delivery_input = {
            "transcript": transcript_text,
            "audioMetrics": audio_metrics or _default_audio_metrics(),
            "wpm": wpm,
        }
        pass3_task = context.call_activity_with_retry(
            "activity_pass3_delivery", RETRY_LLM,
            delivery_input,
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
        except Exception:
            classified_segments = transcript_result["segments"]
            log.warning(f"Segment classification failed for {sermon_id}, using defaults")

        # ── Normalize + composite ──
        raw_scores = {**pass1, **pass2, **pass3}
        sermon_type = classification["sermonType"]
        confidence = classification["confidence"]

        categories, norm_applied = normalize_scores(raw_scores, sermon_type, confidence)
        composite = compute_composite(categories)

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

        yield context.call_activity("activity_update_sermon", {
            "sermonId": sermon_id,
            "updates": updates,
        })

    except Exception as e:
        log.error(f"Pipeline failed for {sermon_id}: {e}")
        yield context.call_activity("activity_update_sermon", {
            "sermonId": sermon_id,
            "updates": fail_sermon_doc(str(e)),
        })


def _default_audio_metrics():
    """Fallback when Parselmouth fails — lets delivery pass still run."""
    return {
        "pitchMeanHz": 0, "pitchStdHz": 0, "pitchRangeHz": 0,
        "intensityMeanDb": 0, "intensityRangeDb": 0, "noiseFloorDb": 0,
        "pauseCount": 0, "pausesPerMinute": 0, "durationSeconds": 0,
    }


# ─────────────────────────────────────────────
#  Activity Function Registrations
# ─────────────────────────────────────────────

from activities import (
    transcribe, analyze_audio, pass1_biblical, pass2_structure,
    pass3_delivery, classify_sermon, classify_segments,
    generate_summary, update_sermon,
)


@bp.activity_trigger(input_name="input")
def activity_transcribe(input: dict):
    return transcribe(input)

@bp.activity_trigger(input_name="input")
def activity_analyze_audio(input: dict):
    return analyze_audio(input)

@bp.activity_trigger(input_name="input")
def activity_pass1_biblical(input: dict):
    return pass1_biblical(input)

@bp.activity_trigger(input_name="input")
def activity_pass2_structure(input: dict):
    return pass2_structure(input)

@bp.activity_trigger(input_name="input")
def activity_pass3_delivery(input: dict):
    return pass3_delivery(input)

@bp.activity_trigger(input_name="input")
def activity_classify_sermon(input: dict):
    return classify_sermon(input)

@bp.activity_trigger(input_name="input")
def activity_classify_segments(input: dict):
    return classify_segments(input)

@bp.activity_trigger(input_name="input")
def activity_generate_summary(input: dict):
    return generate_summary(input)

@bp.activity_trigger(input_name="input")
def activity_update_sermon(input: dict):
    return update_sermon(input)


app.register_functions(bp)
