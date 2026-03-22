"""Activity functions for the sermon processing pipeline.

Re-exports all activities from submodules for backward compatibility.
"""

import os  # noqa: F401 — tests patch activities.os
import tempfile  # noqa: F401 — tests patch activities.tempfile

# Shared clients (re-exported so patches like @patch("activities._openai_client") still work)
from activities.helpers import (  # noqa: F401
    _openai_client, _cosmos_client, _blob_client, _default_audio, log,
)

from activities.transcription import transcribe, analyze_audio  # noqa: F401
from activities.scoring import (  # noqa: F401
    pass1_biblical, pass2_structure, pass3_delivery, pass4_enrichment,
    classify_sermon, classify_segments, generate_summary,
)
from activities.rescore import rescore_sermon  # noqa: F401
from activities.church import ensure_church  # noqa: F401
from activities.misc import (  # noqa: F401
    update_sermon, detect_ai_generation, summarize_sermon_content, download_rss_audio,
)
