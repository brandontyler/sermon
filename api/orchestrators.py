"""Durable Functions orchestrators + activity registrations."""

import time

import azure.durable_functions as df

from log import log
from schema import (
    normalize_scores, compute_composite, fail_sermon_doc,
    PIPELINE_VERSION, SCORING_MODELS, PASS_HASHES,
)
from helpers import _default_audio_metrics
from activities import (
    transcribe, analyze_audio, pass1_biblical, pass2_structure,
    pass3_delivery, pass4_enrichment, classify_sermon, classify_segments,
    generate_summary, update_sermon, rescore_sermon, detect_ai_generation,
    summarize_sermon_content, download_rss_audio, ensure_church,
)

bp = df.Blueprint()

RETRY_LLM = df.RetryOptions(
    first_retry_interval_in_milliseconds=60_000,
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

        _set_status(context, sermon_id, "scoring")

        pass1_task = context.call_activity_with_retry("activity_pass1_biblical", RETRY_LLM, {"transcript": transcript_text})
        pass2_task = context.call_activity_with_retry("activity_pass2_structure", RETRY_LLM, {"transcript": transcript_text})
        pass3_task = context.call_activity_with_retry("activity_pass3_delivery", RETRY_LLM, {
            "transcript": transcript_text,
            "audioMetrics": audio_metrics or _default_audio_metrics(),
            "wpm": wpm,
            "audioAvailable": audio_metrics is not None,
        })
        classify_task = context.call_activity_with_retry("activity_classify_sermon", RETRY_LLM, {
            "transcript": transcript_text,
            "userTitle": input_data.get("userTitle"),
            "userPastor": input_data.get("userPastor"),
        })
        segment_task = context.call_activity_with_retry("activity_classify_segments", RETRY_LIGHT, {"segments": transcript_result["segments"]})
        pass4_task = context.call_activity_with_retry("activity_pass4_enrichment", RETRY_LLM, {"transcript": transcript_text})
        ai_detect_task = context.call_activity_with_retry("activity_detect_ai", RETRY_LIGHT, {"transcript": transcript_text})
        content_summary_task = context.call_activity_with_retry("activity_summarize_content", RETRY_LIGHT, {"transcript": transcript_text})

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
            enrichment = (yield pass4_task).get("enrichment")
        except Exception as e:
            enrichment = None
            if not context.is_replaying:
                log.warning(f"[orchestrator] {sermon_id}: pass4 enrichment failed ({e}), skipping")

        try:
            ai_result = yield ai_detect_task
            ai_score = ai_result.get("aiScore")
            ai_reasoning = ai_result.get("aiReasoning")
        except Exception as e:
            ai_score = ai_reasoning = None
            if not context.is_replaying:
                log.warning(f"[orchestrator] {sermon_id}: AI detection failed ({e}), skipping")

        try:
            content_summary = (yield content_summary_task).get("sermonSummary")
        except Exception as e:
            content_summary = None
            if not context.is_replaying:
                log.warning(f"[orchestrator] {sermon_id}: content summary failed ({e}), skipping")

        _set_status(context, sermon_id, "finalizing")

        raw_scores = {**pass1, **pass2, **pass3}
        sermon_type = classification["sermonType"]
        confidence = classification["confidence"]

        categories, norm_applied = normalize_scores(raw_scores, sermon_type, confidence)
        composite = compute_composite(categories)
        raw_score_map = {k: raw_scores[k]["score"] for k in raw_scores}

        if not context.is_replaying:
            log.info(f"[orchestrator] {sermon_id}: PSR={composite}, type={sermon_type} ({confidence}%)")

        summary_result = yield context.call_activity_with_retry(
            "activity_generate_summary", RETRY_LIGHT,
            {"categories": categories, "sermonType": sermon_type},
        )

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
            "transcript": {"fullText": transcript_text, "segments": classified_segments},
            "classificationConfidence": confidence,
            "normalizationApplied": norm_applied,
            "rawScores": raw_score_map,
            "audioMetrics": audio_metrics,
            "wpmFlag": wpm_flag,
            "enrichment": enrichment,
            "aiScore": ai_score,
            "aiReasoning": ai_reasoning,
            "sermonSummary": content_summary,
            "pipelineVersion": PIPELINE_VERSION,
            "scoringModels": SCORING_MODELS,
            "passVersions": PASS_HASHES,
        }

        yield context.call_activity_with_retry("activity_update_sermon", RETRY_LIGHT, {
            "sermonId": sermon_id, "updates": updates,
        })

        try:
            yield context.call_activity_with_retry("activity_ensure_church", RETRY_LIGHT, {
                "pastor": classification["pastor"], "sermonId": sermon_id,
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
                "sermonId": sermon_id, "updates": fail_sermon_doc(str(e)),
            })
        except Exception as update_err:
            if not context.is_replaying:
                log.critical(
                    f"[orchestrator] {sermon_id}: DOUBLE FAULT — pipeline failed ({e}) "
                    f"AND error recording failed ({update_err}). Sermon stuck at 'processing'."
                )


@bp.orchestration_trigger(context_name="context")
def text_sermon_orchestrator(context: df.DurableOrchestrationContext):
    """Pipeline for text-only sermons: skip transcription + Parselmouth."""
    input_data = context.get_input()
    sermon_id = input_data["sermonId"]
    transcript_text = input_data["transcript"]
    word_count = input_data["wordCount"]

    try:
        estimated_duration = word_count / 140 * 60
        wpm = 140.0

        paragraphs = [p.strip() for p in transcript_text.split("\n") if p.strip()]
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
        segments = [{"start": round(i * seg_duration, 2), "end": round((i + 1) * seg_duration, 2), "text": para, "type": "teaching"} for i, para in enumerate(paragraphs)]

        _set_status(context, sermon_id, "scoring")

        pass1_task = context.call_activity_with_retry("activity_pass1_biblical", RETRY_LLM, {"transcript": transcript_text})
        pass2_task = context.call_activity_with_retry("activity_pass2_structure", RETRY_LLM, {"transcript": transcript_text})
        pass3_task = context.call_activity_with_retry("activity_pass3_delivery", RETRY_LLM, {
            "transcript": transcript_text, "audioMetrics": _default_audio_metrics(), "wpm": wpm, "audioAvailable": False,
        })
        classify_task = context.call_activity_with_retry("activity_classify_sermon", RETRY_LLM, {
            "transcript": transcript_text, "userTitle": input_data.get("userTitle"), "userPastor": input_data.get("userPastor"),
        })
        segment_task = context.call_activity_with_retry("activity_classify_segments", RETRY_LIGHT, {"segments": segments})
        pass4_task = context.call_activity_with_retry("activity_pass4_enrichment", RETRY_LLM, {"transcript": transcript_text})
        ai_detect_task = context.call_activity_with_retry("activity_detect_ai", RETRY_LIGHT, {"transcript": transcript_text})
        content_summary_task = context.call_activity_with_retry("activity_summarize_content", RETRY_LIGHT, {"transcript": transcript_text})

        pass1 = yield pass1_task
        pass2 = yield pass2_task
        pass3 = yield pass3_task
        classification = yield classify_task

        try:
            classified_segments = yield segment_task
        except Exception:
            classified_segments = segments
        try:
            enrichment = (yield pass4_task).get("enrichment")
        except Exception:
            enrichment = None
        try:
            ai_result = yield ai_detect_task
            ai_score, ai_reasoning = ai_result.get("aiScore"), ai_result.get("aiReasoning")
        except Exception:
            ai_score = ai_reasoning = None
        try:
            content_summary = (yield content_summary_task).get("sermonSummary")
        except Exception:
            content_summary = None

        _set_status(context, sermon_id, "finalizing")

        raw_scores = {**pass1, **pass2, **pass3}
        sermon_type = classification["sermonType"]
        confidence = classification["confidence"]

        categories, norm_applied = normalize_scores(raw_scores, sermon_type, confidence, audio_available=False)
        composite = compute_composite(categories)
        raw_score_map = {k: raw_scores[k]["score"] for k in raw_scores}

        if not context.is_replaying:
            log.info(f"[text_orchestrator] {sermon_id}: PSR={composite}, type={sermon_type} ({confidence}%)")

        summary_result = yield context.call_activity_with_retry(
            "activity_generate_summary", RETRY_LIGHT,
            {"categories": categories, "sermonType": sermon_type},
        )

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
            "transcript": {"fullText": transcript_text, "segments": classified_segments},
            "classificationConfidence": confidence,
            "normalizationApplied": norm_applied,
            "rawScores": raw_score_map,
            "audioMetrics": None,
            "inputType": "text",
            "wpmFlag": False,
            "enrichment": enrichment,
            "aiScore": ai_score,
            "aiReasoning": ai_reasoning,
            "sermonSummary": content_summary,
            "pipelineVersion": PIPELINE_VERSION,
            "scoringModels": SCORING_MODELS,
            "passVersions": PASS_HASHES,
        }

        yield context.call_activity_with_retry("activity_update_sermon", RETRY_LIGHT, {
            "sermonId": sermon_id, "updates": updates,
        })

        try:
            yield context.call_activity_with_retry("activity_ensure_church", RETRY_LIGHT, {
                "pastor": classification["pastor"], "sermonId": sermon_id,
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
                "sermonId": sermon_id, "updates": fail_sermon_doc(str(e)),
            })
        except Exception as update_err:
            if not context.is_replaying:
                log.critical(
                    f"[text_orchestrator] {sermon_id}: DOUBLE FAULT — pipeline failed ({e}) "
                    f"AND error recording failed ({update_err}). Sermon stuck at 'processing'."
                )


@bp.orchestration_trigger(context_name="context")
def rss_sermon_orchestrator(context: df.DurableOrchestrationContext):
    """Pipeline for RSS episodes: download audio → upload to blob → run normal audio pipeline."""
    input_data = context.get_input()
    sermon_id = input_data["sermonId"]
    audio_url = input_data["audioUrl"]

    try:
        _set_status(context, sermon_id, "downloading")

        blob_result = yield context.call_activity_with_retry(
            "activity_download_rss_audio", RETRY_TRANSCRIBE,
            {"sermonId": sermon_id, "audioUrl": audio_url},
        )
        blob_url = blob_result["blobUrl"]

        _set_status(context, sermon_id, "transcribing")

        transcribe_task = context.call_activity_with_retry("activity_transcribe", RETRY_TRANSCRIBE, {"blobUrl": blob_url, "sermonId": sermon_id})
        audio_task = context.call_activity_with_retry("activity_analyze_audio", RETRY_LIGHT, {"blobUrl": blob_url})

        transcript_result = yield transcribe_task
        try:
            audio_metrics = yield audio_task
        except Exception as e:
            audio_metrics = None
            if not context.is_replaying:
                log.warning(f"[rss_orchestrator] {sermon_id}: Parselmouth failed ({e})")

        transcript_text = transcript_result["fullText"]
        wpm = transcript_result["wpm"]
        wpm_flag = wpm < 80 or wpm > 200

        _set_status(context, sermon_id, "scoring")

        pass1_task = context.call_activity_with_retry("activity_pass1_biblical", RETRY_LLM, {"transcript": transcript_text})
        pass2_task = context.call_activity_with_retry("activity_pass2_structure", RETRY_LLM, {"transcript": transcript_text})
        pass3_task = context.call_activity_with_retry("activity_pass3_delivery", RETRY_LLM, {
            "transcript": transcript_text, "audioMetrics": audio_metrics or _default_audio_metrics(),
            "wpm": wpm, "audioAvailable": audio_metrics is not None,
        })
        classify_task = context.call_activity_with_retry("activity_classify_sermon", RETRY_LLM, {
            "transcript": transcript_text, "userTitle": input_data.get("userTitle"), "userPastor": None,
        })
        segment_task = context.call_activity_with_retry("activity_classify_segments", RETRY_LIGHT, {"segments": transcript_result["segments"]})
        pass4_task = context.call_activity_with_retry("activity_pass4_enrichment", RETRY_LLM, {"transcript": transcript_text})
        ai_detect_task = context.call_activity_with_retry("activity_detect_ai", RETRY_LIGHT, {"transcript": transcript_text})
        content_summary_task = context.call_activity_with_retry("activity_summarize_content", RETRY_LIGHT, {"transcript": transcript_text})

        pass1 = yield pass1_task
        pass2 = yield pass2_task
        pass3 = yield pass3_task
        classification = yield classify_task

        try:
            classified_segments = yield segment_task
        except Exception:
            classified_segments = transcript_result["segments"]
        try:
            enrichment = (yield pass4_task).get("enrichment")
        except Exception:
            enrichment = None
        try:
            ai_result = yield ai_detect_task
            ai_score, ai_reasoning = ai_result.get("aiScore"), ai_result.get("aiReasoning")
        except Exception:
            ai_score = ai_reasoning = None
        try:
            content_summary = (yield content_summary_task).get("sermonSummary")
        except Exception:
            content_summary = None

        _set_status(context, sermon_id, "finalizing")

        raw_scores = {**pass1, **pass2, **pass3}
        sermon_type = classification["sermonType"]
        confidence = classification["confidence"]
        categories, norm_applied = normalize_scores(raw_scores, sermon_type, confidence)
        composite = compute_composite(categories)
        raw_score_map = {k: raw_scores[k]["score"] for k in raw_scores}

        summary_result = yield context.call_activity_with_retry(
            "activity_generate_summary", RETRY_LIGHT,
            {"categories": categories, "sermonType": sermon_type},
        )

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
            "transcript": {"fullText": transcript_text, "segments": classified_segments},
            "classificationConfidence": confidence,
            "normalizationApplied": norm_applied,
            "rawScores": raw_score_map,
            "audioMetrics": audio_metrics,
            "wpmFlag": wpm_flag,
            "enrichment": enrichment,
            "aiScore": ai_score,
            "aiReasoning": ai_reasoning,
            "sermonSummary": content_summary,
            "blobUrl": blob_url,
            "pipelineVersion": PIPELINE_VERSION,
            "scoringModels": SCORING_MODELS,
            "passVersions": PASS_HASHES,
        }

        yield context.call_activity_with_retry("activity_update_sermon", RETRY_LIGHT, {
            "sermonId": sermon_id, "updates": updates,
        })

        try:
            yield context.call_activity_with_retry("activity_ensure_church", RETRY_LIGHT, {
                "pastor": classification["pastor"], "sermonId": sermon_id,
            })
        except Exception:
            pass

        _set_status(context, sermon_id, "complete")

    except Exception as e:
        if not context.is_replaying:
            log.error(f"[rss_orchestrator] {sermon_id}: pipeline failed: {e}", exc_info=True)
        _set_status(context, sermon_id, "failed")
        try:
            yield context.call_activity_with_retry("activity_update_sermon", RETRY_LIGHT, {
                "sermonId": sermon_id, "updates": fail_sermon_doc(str(e)),
            })
        except Exception:
            pass


@bp.orchestration_trigger(context_name="context")
def rescore_orchestrator(context: df.DurableOrchestrationContext):
    """Re-score sermons using existing transcripts."""
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
#  Activity Function Registrations
# ─────────────────────────────────────────────

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
def activity_detect_ai(input: dict):
    return _run_activity("detect_ai", detect_ai_generation, input)

@bp.activity_trigger(input_name="input")
def activity_summarize_content(input: dict):
    return _run_activity("summarize_content", summarize_sermon_content, input)

@bp.activity_trigger(input_name="input")
def activity_rescore_sermon(input: dict):
    return _run_activity("rescore_sermon", rescore_sermon, input)

@bp.activity_trigger(input_name="input")
def activity_download_rss_audio(input: dict):
    return _run_activity("download_rss_audio", download_rss_audio, input)
