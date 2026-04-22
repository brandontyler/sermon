"""Shared helpers used across route modules."""

import json
import os

import azure.functions as func


ALLOWED_TYPES = {
    "audio/mpeg": ".mp3",
    "audio/wav": ".wav",
    "audio/x-wav": ".wav",
    "audio/wave": ".wav",
    "audio/mp4": ".m4a",
    "audio/x-m4a": ".m4a",
}
MAX_SIZE = 100 * 1024 * 1024  # 100MB

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


_ALLOWED_ORIGIN_SUFFIXES = (".howwas.church",)
_ALLOWED_ORIGINS_EXACT = frozenset()  # add exact origins here if needed


def _cors_origin(req) -> str | None:
    """Return the request Origin if it matches *.howwas.church or localhost."""
    origin = req.headers.get("Origin") if req else None
    if not origin:
        return None
    # Strip protocol for suffix check
    host = origin.split("://", 1)[-1].rstrip("/")
    if any(host == s.lstrip(".") or host.endswith(s) for s in _ALLOWED_ORIGIN_SUFFIXES):
        return origin
    if host.startswith("localhost"):
        return origin
    if origin in _ALLOWED_ORIGINS_EXACT:
        return origin
    return None


def _json_response(body, status=200, headers=None, req=None):
    resp = func.HttpResponse(
        json.dumps(body, default=str),
        status_code=status,
        mimetype="application/json",
    )
    if headers:
        for k, v in headers.items():
            resp.headers[k] = v
    # Dynamic CORS for *.howwas.church subdomains
    origin = _cors_origin(req) if req else None
    if origin:
        resp.headers["Access-Control-Allow-Origin"] = origin
    return resp


def _require_admin(req):
    """Check SWA client principal (Entra ID) or fallback to admin key.

    Returns None if authorized, or an HttpResponse 401 if not.
    """
    principal = req.headers.get("x-ms-client-principal")
    if principal:
        import base64
        try:
            data = json.loads(base64.b64decode(principal + "=="))
            if "admin" in data.get("userRoles", []):
                return None
        except Exception:
            pass

    admin_key = os.environ.get("ADMIN_KEY", "")
    provided = req.headers.get("x-admin-key", "") or req.params.get("key", "")
    if admin_key and provided == admin_key:
        return None

    return _json_response({"error": "Unauthorized"}, 401)


def _feeds_container():
    """Get or create the feeds Cosmos container."""
    from azure.cosmos import CosmosClient
    cosmos = CosmosClient.from_connection_string(os.environ["COSMOS_CONNECTION_STRING"])
    db = cosmos.get_database_client("psr")
    try:
        return db.create_container_if_not_exists(id="feeds", partition_key={"paths": ["/id"], "kind": "Hash"})
    except Exception:
        return db.get_container_client("feeds")


def _extract_text(file_bytes, filename, content_type):
    """Extract plain text from uploaded file. Returns str or raises ValueError."""
    import re
    ext = os.path.splitext(filename)[1].lower() if filename else ""

    if ext in {".txt", ".md", ".csv", ".xml", ".html", ".htm"} or content_type in {"text/plain", "text/markdown", "text/csv", "text/xml", "text/html"}:
        for enc in ("utf-8", "utf-8-sig", "latin-1"):
            try:
                return file_bytes.decode(enc)
            except (UnicodeDecodeError, ValueError):
                continue
        raise ValueError("Could not decode text file")

    if ext == ".docx" or content_type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
        import zipfile, io, xml.etree.ElementTree as ET
        with zipfile.ZipFile(io.BytesIO(file_bytes)) as z:
            xml_content = z.read("word/document.xml")
        root = ET.fromstring(xml_content)
        ns = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
        return "\n".join(p.text for p in root.iter(f"{{{ns['w']}}}t") if p.text)

    if ext == ".pdf" or content_type == "application/pdf":
        raise ValueError("PDF upload not yet supported — please copy/paste the text into a .txt file")

    if ext == ".doc" or content_type == "application/msword":
        raise ValueError(".doc format not supported — please save as .docx or .txt")

    if ext == ".rtf" or content_type in {"text/rtf", "application/rtf"}:
        text = file_bytes.decode("latin-1")
        text = re.sub(r'\\[a-z]+\d*\s?', '', text)
        text = re.sub(r'[{}]', '', text)
        return text.strip()

    if ext == ".odt" or content_type == "application/vnd.oasis.opendocument.text":
        import zipfile, io, xml.etree.ElementTree as ET
        with zipfile.ZipFile(io.BytesIO(file_bytes)) as z:
            xml_content = z.read("content.xml")
        root = ET.fromstring(xml_content)
        ns = {"text": "urn:oasis:names:tc:opendocument:xmlns:text:1.0"}
        return "\n".join("".join(p.itertext()) for p in root.iter(f"{{{ns['text']}}}p"))

    raise ValueError(f"Unsupported file type: {ext or content_type}")


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


def _default_audio_metrics():
    """Fallback when Parselmouth fails — lets delivery pass still run."""
    return {
        "pitchMeanHz": 0, "pitchStdHz": 0, "pitchRangeHz": 0,
        "intensityMeanDb": 0, "intensityRangeDb": 0, "noiseFloorDb": 0,
        "pauseCount": 0, "pausesPerMinute": 0, "durationSeconds": 0,
    }
