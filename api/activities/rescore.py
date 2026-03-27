"""Rescore activity — re-scores sermons using current models."""

from activities.helpers import _openai_client, _cosmos_client, _default_audio, log
from activities.scoring import (
    pass1_biblical, pass2_structure, pass3_delivery, pass4_enrichment,
    classify_sermon, classify_segments, generate_summary,
)
from activities.misc import update_sermon


def rescore_sermon(input_data):
    """Re-score a sermon using current models on its existing transcript.

    Supports selective per-pass rescore via input_data["passes"].
    """
    from schema import (normalize_scores, compute_composite, PIPELINE_VERSION,
                        SCORING_MODELS, PASS_HASHES, PASS_CATEGORIES, detect_stale_passes)
    import datetime

    container = _cosmos_client()
    sermon_id = input_data["sermonId"]
    doc = container.read_item(sermon_id, partition_key=sermon_id)

    if doc.get("status") != "complete":
        return {"ok": False, "error": "sermon not complete"}

    transcript = doc["transcript"]["fullText"]
    audio_metrics = doc.get("audioMetrics")
    duration = doc.get("duration") or 0
    word_count = len(transcript.split())
    wpm = round(word_count / (duration / 60), 1) if duration > 0 else 130

    requested = input_data.get("passes")
    if requested is None:
        run_passes = {"pass1", "pass2", "pass3", "pass4", "classify", "segments", "summary"}
    else:
        run_passes = set()
        for p in requested:
            if p == "stale":
                run_passes.update(detect_stale_passes(doc))
            elif isinstance(p, int):
                run_passes.add(f"pass{p}")
            else:
                run_passes.add(p)

    if not run_passes:
        return {"ok": True, "compositePsr": doc.get("compositePsr"), "passesRun": [], "message": "all passes up to date"}

    log.info(f"[rescore] {sermon_id}: running passes {sorted(run_passes)}")

    existing_cats = doc.get("categories", {})
    scoring_changed = any(p in run_passes for p in ("pass1", "pass2", "pass3"))

    raw_scores = {}
    if "pass1" in run_passes:
        raw_scores.update(pass1_biblical({"transcript": transcript}))
    else:
        for k in PASS_CATEGORIES["pass1"]:
            raw_scores[k] = {"score": existing_cats.get(k, {}).get("score", 0),
                             "reasoning": existing_cats.get(k, {}).get("reasoning", "")}

    if "pass2" in run_passes:
        raw_scores.update(pass2_structure({"transcript": transcript}))
    else:
        for k in PASS_CATEGORIES["pass2"]:
            raw_scores[k] = {"score": existing_cats.get(k, {}).get("score", 0),
                             "reasoning": existing_cats.get(k, {}).get("reasoning", "")}

    if "pass3" in run_passes:
        raw_scores.update(pass3_delivery({
            "transcript": transcript,
            "audioMetrics": audio_metrics or _default_audio(),
            "wpm": wpm,
            "audioAvailable": audio_metrics is not None,
        }))
    else:
        for k in PASS_CATEGORIES["pass3"]:
            raw_scores[k] = {"score": existing_cats.get(k, {}).get("score", 0),
                             "reasoning": existing_cats.get(k, {}).get("reasoning", "")}

    if "classify" in run_passes or scoring_changed:
        classification = classify_sermon({
            "transcript": transcript, "userTitle": doc.get("title"), "userPastor": doc.get("pastor"),
        })
        run_passes.add("classify")
    else:
        classification = {"sermonType": doc.get("sermonType", "topical"),
                          "confidence": doc.get("classificationConfidence", 50)}

    if scoring_changed:
        categories, norm_applied = normalize_scores(
            raw_scores, classification["sermonType"], classification["confidence"],
            audio_available=audio_metrics is not None)
        composite = compute_composite(categories)
    else:
        categories = existing_cats
        norm_applied = doc.get("normalizationApplied", "none")
        composite = doc.get("compositePsr")
        consistency_flags = doc.get("consistencyFlags", [])

    if "pass4" in run_passes:
        try:
            enrichment = pass4_enrichment({"transcript": transcript}).get("enrichment")
        except Exception as e:
            enrichment = doc.get("enrichment")
            log.warning(f"[rescore] {sermon_id}: pass4 failed ({e}), keeping existing")
    else:
        enrichment = doc.get("enrichment")

    # Apply consistency check now that enrichment is available
    if scoring_changed:
        from schema import consistency_check
        categories, consistency_flags = consistency_check(categories, enrichment)
        composite = compute_composite(categories)

    existing_segs = doc.get("transcript", {}).get("segments", [])
    if "segments" in run_passes:
        if len(existing_segs) <= 3 and word_count > 200:
            import re
            sentences = re.split(r'(?<=[.!?])\s+', transcript.strip())
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
            if len(chunks) > 3:
                dur = doc.get("duration") or (word_count / 140 * 60)
                seg_dur = dur / len(chunks)
                existing_segs = [{"start": round(i * seg_dur, 2), "end": round((i + 1) * seg_dur, 2),
                                  "text": c, "type": "teaching"} for i, c in enumerate(chunks)]
        try:
            classified_segs = classify_segments({"segments": existing_segs})
        except Exception as e:
            classified_segs = existing_segs
            log.warning(f"[rescore] {sermon_id}: segment reclassification failed ({e})")
    else:
        classified_segs = existing_segs

    if "summary" in run_passes or scoring_changed:
        summary = generate_summary({"categories": categories, "sermonType": classification["sermonType"]})
        run_passes.add("summary")
    else:
        summary = {"strengths": doc.get("strengths"), "improvements": doc.get("improvements"), "summary": doc.get("summary")}

    pass_versions = doc.get("passVersions", {})
    for p in run_passes:
        if p in PASS_HASHES:
            pass_versions[p] = PASS_HASHES[p]

    previous = doc.get("previousScores", [])
    if scoring_changed:
        previous.append({
            "compositePsr": doc.get("compositePsr"),
            "categories": doc.get("categories"),
            "pipelineVersion": doc.get("pipelineVersion", "pre-tracking"),
            "rescoredAt": datetime.datetime.utcnow().isoformat() + "Z",
        })

    updates = {
        "passVersions": pass_versions,
        "pipelineVersion": PIPELINE_VERSION,
        "scoringModels": SCORING_MODELS,
        "rescoredAt": datetime.datetime.utcnow().isoformat() + "Z",
    }
    if scoring_changed:
        updates.update({
            "compositePsr": composite, "categories": categories,
            "sermonType": classification["sermonType"],
            "classificationConfidence": classification["confidence"],
            "normalizationApplied": norm_applied,
            "rawScores": {k: raw_scores[k]["score"] for k in raw_scores},
            "strengths": summary.get("strengths"), "improvements": summary.get("improvements"),
            "summary": summary.get("summary"), "previousScores": previous,
            "consistencyFlags": consistency_flags,
        })
    if "pass4" in run_passes:
        updates["enrichment"] = enrichment
    if "segments" in run_passes:
        updates["transcript"] = {"fullText": transcript, "segments": classified_segs}
    if not scoring_changed and "summary" in run_passes:
        updates.update({"strengths": summary.get("strengths"), "improvements": summary.get("improvements"),
                        "summary": summary.get("summary")})

    update_sermon({"sermonId": sermon_id, "updates": updates})

    return {"ok": True, "compositePsr": composite, "passesRun": sorted(run_passes)}
