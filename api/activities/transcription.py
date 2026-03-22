"""Transcription and audio analysis activities."""

import os
import tempfile

import numpy as np

from activities.helpers import _blob_client, log


def transcribe(input_data):
    """Transcribe audio via Azure AI Speech fast transcription API."""
    from azure.storage.blob import BlobClient
    from azure.core.credentials import AzureKeyCredential
    from azure.ai.transcription import TranscriptionClient
    from azure.ai.transcription.models import TranscriptionContent, TranscriptionOptions

    blob = BlobClient.from_connection_string(
        os.environ["STORAGE_CONNECTION_STRING"], "sermon-audio", input_data["blobUrl"]
    )
    audio_bytes = blob.download_blob().readall()

    client = TranscriptionClient(
        endpoint=os.environ["SPEECH_ENDPOINT"],
        credential=AzureKeyCredential(os.environ["SPEECH_KEY"]),
    )

    ext = os.path.splitext(input_data["blobUrl"])[1] or ".mp3"
    with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as f:
        f.write(audio_bytes)
        tmp_path = f.name

    try:
        with open(tmp_path, "rb") as audio_file:
            options = TranscriptionOptions(locales=["en-US"])
            content = TranscriptionContent(definition=options, audio=audio_file)
            result = client.transcribe(content)
    finally:
        os.unlink(tmp_path)

    full_text = result.combined_phrases[0].text if result.combined_phrases else ""
    duration_ms = result.duration_milliseconds or 0
    word_count = len(full_text.split())
    wpm = round(word_count / (duration_ms / 60000), 1) if duration_ms > 0 else 0

    segments = []
    if result.phrases:
        for phrase in result.phrases:
            offset_ms = phrase.offset_milliseconds or 0
            dur_ms = phrase.duration_milliseconds or 0
            segments.append({
                "start": round(offset_ms / 1000, 2),
                "end": round((offset_ms + dur_ms) / 1000, 2),
                "text": phrase.text,
                "type": "teaching",
            })

    return {
        "fullText": full_text,
        "wordCount": word_count,
        "durationMs": int(duration_ms),
        "wpm": wpm,
        "segments": segments,
    }


def analyze_audio(input_data):
    """Extract pitch, intensity, pause metrics via Parselmouth."""
    import parselmouth
    import subprocess

    blob = _blob_client(input_data["blobUrl"])
    audio_bytes = blob.download_blob().readall()

    ext = os.path.splitext(input_data["blobUrl"])[1] or ".mp3"
    with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as f:
        f.write(audio_bytes)
        tmp_path = f.name

    down_path = tmp_path + ".16k.wav"
    try:
        subprocess.run(
            ["ffmpeg", "-y", "-i", tmp_path, "-ac", "1", "-ar", "16000", down_path],
            capture_output=True, timeout=120,
        )
        os.unlink(tmp_path)
        snd = parselmouth.Sound(down_path)
    except Exception:
        down_path = None
        snd = parselmouth.Sound(tmp_path)
    finally:
        for p in [tmp_path, down_path]:
            if p:
                try:
                    os.unlink(p)
                except OSError:
                    pass

    pitch = snd.to_pitch(time_step=0.1)
    intensity = snd.to_intensity(time_step=0.1)

    pv = pitch.selected_array["frequency"]
    voiced = pv[pv > 0]
    iv = intensity.values[0]

    noise_floor = float(np.percentile(iv, 5))
    iv_filtered = iv[iv > noise_floor]

    threshold = float(np.percentile(iv, 20))
    transitions = np.diff((iv < threshold).astype(int))
    pause_count = int(np.sum(transitions == 1))

    return {
        "pitchMeanHz": round(float(np.mean(voiced)), 1) if len(voiced) > 0 else 0,
        "pitchStdHz": round(float(np.std(voiced)), 1) if len(voiced) > 0 else 0,
        "pitchRangeHz": round(float(np.max(voiced) - np.min(voiced)), 1) if len(voiced) > 0 else 0,
        "intensityMeanDb": round(float(np.mean(iv_filtered)), 1) if len(iv_filtered) > 0 else 0,
        "intensityRangeDb": round(float(np.max(iv_filtered) - np.min(iv_filtered)), 1) if len(iv_filtered) > 0 else 0,
        "noiseFloorDb": round(noise_floor, 1),
        "pauseCount": pause_count,
        "pausesPerMinute": round(pause_count / (snd.duration / 60), 1) if snd.duration > 0 else 0,
        "durationSeconds": round(snd.duration, 1),
    }
