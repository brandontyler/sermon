# Admin Authentication — Research & Design

## Current State
- Admin pages (`/admin`, `/admin/manage`, `/admin/feeds`) protected by shared admin key in text input
- Backend endpoints check `x-admin-key` header against `ADMIN_KEY` env var
- No real user identity, no session, no login/logout flow
- SWA plan: **Free tier**

## Decision: SWA Built-in Auth with Microsoft Entra ID

Using the pre-configured Entra ID (AAD) provider on the SWA Free tier. This lets anyone with a Microsoft account (Outlook, Hotmail, Live, work M365) log in — no GitHub account needed.

### Why Entra ID over GitHub
- Orlando may not have a GitHub account
- Everyone has a Microsoft account (or can create one free)
- Pre-configured on SWA Free tier — zero setup, zero cost
- Block GitHub provider to keep it simple (one login button)

### How SWA Built-in Auth Works

SWA handles the entire OAuth flow at the reverse proxy level. No auth libraries or tokens in our code.

1. User visits `/admin` → SWA checks route rules → requires `admin` role
2. Not logged in → 401 → `responseOverrides` redirects to `/.auth/login/aad`
3. Microsoft OAuth flow → user signs in with Microsoft account
4. SWA sets session cookie, checks role → user has `admin`? → serve page
5. All API requests through SWA get `x-ms-client-principal` header injected automatically

### x-ms-client-principal Header

Base64-encoded JSON injected by SWA on every request through the SWA domain:

```json
{
  "identityProvider": "aad",
  "userId": "abc123def456",
  "userDetails": "brandon@example.com",
  "userRoles": ["anonymous", "authenticated", "admin"]
}
```

Backend decodes this instead of checking admin key.

### Invitation System (One-Time Setup)

Invite users via Azure CLI — assigns the `admin` custom role to specific Microsoft accounts:

```bash
# Invite Brandon
az staticwebapp users invite \
  -n psr-web-dev -g rg-sermon-rating-dev \
  --authentication-provider AAD \
  --user-details "<brandon-microsoft-email>" \
  --roles "admin" \
  --domain gentle-ground-0713e880f.1.azurestaticapps.net \
  --invitation-expiration-in-hours 168

# Invite Orlando
az staticwebapp users invite \
  -n psr-web-dev -g rg-sermon-rating-dev \
  --authentication-provider AAD \
  --user-details "<orlando-microsoft-email>" \
  --roles "admin" \
  --domain gentle-ground-0713e880f.1.azurestaticapps.net \
  --invitation-expiration-in-hours 168
```

Each person clicks the generated link, signs in with their Microsoft account, and the `admin` role is permanently assigned. Up to 25 invitation slots on Free tier (plenty).

Can also be done in Azure Portal: SWA → Settings → Role Management → Invite.

### Implementation Plan

**1. staticwebapp.config.json changes:**
```json
{
  "routes": [
    { "route": "/.auth/login/github", "statusCode": 404 },
    { "route": "/admin*", "allowedRoles": ["admin"] },
    { "route": "/church-admin*", "allowedRoles": ["admin"] },
    { "route": "/api/feeds*", "methods": ["GET","POST","PATCH","DELETE"], "allowedRoles": ["admin"] },
    { "route": "/api/sermons/*", "methods": ["DELETE","PATCH"], "allowedRoles": ["admin"] },
    { "route": "/api/rescore", "methods": ["POST"], "allowedRoles": ["admin"] },
    ...existing routes...
  ],
  "responseOverrides": {
    "401": {
      "redirect": "/.auth/login/aad?post_login_redirect_uri=.referrer",
      "statusCode": 302
    }
  }
}
```

**2. Backend changes:**
- New helper: `_get_auth_user(req)` — parses `x-ms-client-principal` header, checks `admin` in roles
- Admin endpoints: check either `x-ms-client-principal` (SWA auth) OR `x-admin-key` (fallback for CLI/direct API)
- Remove admin key as the primary auth mechanism

**3. Frontend changes:**
- Remove admin key `<input>` from all admin pages
- Add auth status bar: show logged-in user + logout link
- Call `/.auth/me` on admin pages to get current user info
- Remove `x-admin-key` header from fetch calls (SWA injects `x-ms-client-principal` automatically)

**4. Post-deploy:**
- Generate invitation links for Brandon + Orlando
- Each clicks link, signs in with Microsoft account → `admin` role assigned

### What's NOT Affected
- Public pages (`/`, `/sermons`, `/upload`, `/dashboard`, `/calculations`, `/churches`) stay anonymous
- RSS timer trigger runs inside Azure Functions, not through SWA — unaffected
- Direct API calls (curl, Postman) still work with `x-admin-key` header as fallback
- `POST /api/sermons` (upload) stays anonymous — anyone can upload

### Edge Cases
- **SWA linked backend**: `x-ms-client-principal` only injected when requests go through SWA domain. Direct calls to `psr-functions-dev.azurewebsites.net` bypass this — admin key covers that.
- **Route protection is server-side**: SWA reverse proxy enforces it before our code runs. Client-side routing alone isn't enough (which is why we also check in the backend).
- **Session duration**: SWA manages session cookies. Default is ~8 hours. User just re-authenticates when it expires.

### Cost
$0 — included in SWA Free tier.
