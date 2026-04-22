"""PSR Function App — registers route blueprints + durable orchestrators."""

import azure.functions as func

import log as _log  # noqa: F401 — init logging config early (silences Azure SDK noise)
from routes import sermons, feeds, churches, admin, users
import orchestrators

app = func.FunctionApp(http_auth_level=func.AuthLevel.ANONYMOUS)

# Register HTTP route blueprints
app.register_functions(sermons.bp)
app.register_functions(feeds.bp)
app.register_functions(churches.bp)
app.register_functions(admin.bp)
app.register_functions(users.bp)

# Register Durable Functions (orchestrators + activities)
app.register_functions(orchestrators.bp)

# ── Re-exports for backward compatibility (tests import from function_app) ──
from helpers import (  # noqa: F401
    ALLOWED_TYPES, MAX_SIZE, ALLOWED_TEXT_TYPES, ALLOWED_TEXT_EXTENSIONS, MAX_TEXT_SIZE,
    _json_response, _require_admin, _feeds_container, _extract_text,
    _extract_video_id, _parse_timestamp, _default_audio_metrics,
)
from routes.sermons import upload_sermon, list_sermons, get_sermon  # noqa: F401
from routes.feeds import (  # noqa: F401
    list_feeds, preview_feeds, poll_feeds_manual,
    _preview_feeds, _poll_all_feeds,
)
