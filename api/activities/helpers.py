"""Shared clients and utilities for activity functions."""

import os

from openai import AzureOpenAI

from log import log


def _openai_client():
    return AzureOpenAI(
        api_key=os.environ["OPENAI_KEY"],
        api_version=os.environ["OPENAI_API_VERSION"],
        azure_endpoint=os.environ["OPENAI_ENDPOINT"],
        max_retries=3,
        timeout=300,
    )


def _cosmos_client():
    from azure.cosmos import CosmosClient
    client = CosmosClient.from_connection_string(os.environ["COSMOS_CONNECTION_STRING"])
    return client.get_database_client("psr").get_container_client("sermons")


def _blob_client(blob_url):
    from azure.storage.blob import BlobClient
    return BlobClient.from_connection_string(os.environ["STORAGE_CONNECTION_STRING"], "sermon-audio", blob_url)


def _default_audio():
    return {
        "pitchMeanHz": 0, "pitchStdHz": 0, "pitchRangeHz": 0,
        "intensityMeanDb": 0, "intensityRangeDb": 0, "noiseFloorDb": 0,
        "pauseCount": 0, "pausesPerMinute": 0, "durationSeconds": 0,
    }


# Prompt template fingerprints for staleness detection.
_PASS_FINGERPRINTS = {
    "pass1": "o4-mini:pass1_biblical:v2026-03-10b:calibration+passage-focus-conditional",
    "pass2": "gpt-5-mini:pass2_structure:v2026-03-10b:calibration+discriminating-questions",
    "pass3": "gpt-5-nano:pass3_delivery:v2026-03-10b:calibration+audio-metrics",
    "pass4": "gpt-5-nano:pass4_enrichment:v2026-03-11a:illustrations-added",
    "classify": "gpt-5-nano:classify_sermon:v2026-03-08a:begin-mid-end-sampling",
    "segments": "gpt-5-nano:classify_segments:v2026-03-08a:batch-200",
    "summary": "gpt-5-nano:generate_summary:v2026-03-10a:3-strengths-2-improvements",
}


def _register_pass_hashes():
    from schema import pass_hash, PASS_HASHES
    for name, fingerprint in _PASS_FINGERPRINTS.items():
        model = fingerprint.split(":")[0]
        PASS_HASHES[name] = pass_hash(fingerprint, model)


_register_pass_hashes()
