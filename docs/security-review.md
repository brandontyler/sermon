# Security & Code Review Findings (2026-04-03)

Comprehensive review from Azure security, Azure developer, and web application perspectives.
Bead: `sermon-rih`

## CRITICAL — Fix immediately

### 1. `_require_admin` accepts forged `x-ms-client-principal` (CONFIRMED EXPLOITABLE)

The Function App is directly accessible at `psr-functions-dev.azurewebsites.net` (not proxied through SWA). Anyone can forge an `x-ms-client-principal` header with `{"userRoles":["authenticated"]}` and call admin endpoints — DELETE sermons, trigger rescores, manage feeds, etc.

**Confirmed:** A forged principal successfully deleted a sermon during testing (Born to Crave, re-ingested via feed poll).

**Root cause:** Two issues compound:
1. `_require_admin()` accepts `authenticated` role as admin (should require `admin` role only)
2. The Function App has no access restrictions — it is publicly accessible, not behind SWA

**Fix options (pick one or both):**
- **Quick:** Remove `authenticated` from `_require_admin`, require `admin` role only. This still allows forged headers on the direct Function App URL, but at least the attacker needs to know the role name.
- **Proper:** Add Function App access restrictions to only allow traffic from SWA (or use SWA linked backend which validates the principal header server-side). Then SWA strips/validates `x-ms-client-principal` so it cannot be forged.
- **Best:** Both. Require `admin` role AND restrict Function App network access.

**Files:** `api/helpers.py` (`_require_admin`), `infra/modules/functions.bicep` (access restrictions)

### 2. Sermon detail endpoint has no tenant scoping

`GET /api/sermons/{id}` returns full sermon data (including transcript) to anyone who knows the ID. No `x-tenant` check, no auth. UUIDs are not secret — they appear in URLs, logs, browser history.

**Fix:** If `x-tenant` header is present, verify `doc["churchId"]` matches before returning. Or add this as a future auth concern.

**File:** `api/routes/sermons.py` (`get_sermon`)

### 3. RSS backfill limit not enforced in all code paths

`backfillCount=10` was set but 260 episodes were ingested on first poll. The backfill limit only applies when `lastPolledAt` is None, but the timer had already set `lastPolledAt` before the manual poll ran, so it fell into the date-filter branch instead.

**Fix:** Apply `backfillCount` as a hard cap regardless of which branch is taken.

**File:** `api/routes/feeds.py` (`_poll_all_feeds`)

## HIGH — Fix before production

### 4. Admin key accepted via query parameter

```python
provided = req.headers.get("x-admin-key", "") or req.params.get("key", "")
```

Query params leak into server logs, browser history, referrer headers. Remove `req.params.get("key", "")`.

**File:** `api/helpers.py`

### 5. `x-tenant` header is unauthenticated

Anyone can add `x-tenant: denton-bible` to API calls and see filtered data. Fine for MVP, but needs auth before handing to a real church with private data.

**File:** `api/routes/sermons.py`

### 6. RSS audio download loads entire file into memory

`resp.content` downloads the full file into memory. On consumption plan (1.5GB), large audio files OOM (confirmed: 88 failures with exit code 137 during initial backfill).

**Fix:** Stream to temp file, then upload to blob in chunks.

**File:** `api/activities/misc.py` (`download_rss_audio`)

## MEDIUM — Fix when convenient

### 7. Rate limiting bypassable via forged X-Forwarded-For

Function App is directly accessible, so clients can set `X-Forwarded-For` to any IP. Rate limiting (5 uploads/hr per IP) is bypassable.

**File:** `api/routes/sermons.py`

### 8. Cosmos and Storage use connection strings instead of managed identity

RBAC roles are assigned in Bicep but unused. Code uses `CosmosClient.from_connection_string()` everywhere. Connection strings are master keys — if leaked, full access.

**Fix:** Switch to `DefaultAzureCredential()`. The RBAC roles are already in place.

**Files:** `api/activities/helpers.py`, `api/helpers.py`, `api/routes/*.py`, `infra/modules/keyvault.bicep`

### 9. Poll not idempotent — crash mid-poll can cause duplicate orchestrator starts

**Fix:** Wrap `create_item` in try/except for 409 Conflict and skip.

**File:** `api/routes/feeds.py`

### 10. No security headers on SWA

Missing: `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `Referrer-Policy: strict-origin-when-cross-origin`.

**File:** `web/public/staticwebapp.config.json`

### 11. Missing `www.howwas.church` in CORS origins

**File:** `infra/modules/functions.bicep`

### 12. No input length validation on title/pastor

No max length on sermon title or pastor name. Suggest 200 char max for title, 100 for pastor.

**Files:** `api/routes/sermons.py`

## LOW — Nice to have

### 13. Cosmos DB public network access with no IP rules
### 14. Cosmos backup is periodic (4hr interval, 8hr retention) — consider continuous
### 15. No diagnostic settings on Cosmos or Storage
### 16. Duplicate Cosmos client instantiation per request — consider singleton
### 17. `new_sermon_doc` defaults date to today for RSS sermons without published_parsed

## Verified non-issues

- `infra/main.json` is NOT tracked in git
- `.env` is gitignored
- Blob public access is disabled
- TLS 1.2 enforced on storage
- FTPS disabled on Function App
- HTTPS-only on Function App
- Key Vault uses RBAC authorization (not access policies)
- Secrets resolved server-side via ARM listKeys()
