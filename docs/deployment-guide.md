# PSR Deployment Guide

Complete checklist for deploying howwas.church to a new Azure subscription from scratch.

## Prerequisites

### Local tools
- **Azure CLI**: `az --version` (2.60+) — [Install](https://learn.microsoft.com/en-us/cli/azure/install-azure-cli)
- **Node.js**: `node --version` (20+) — [Install](https://nodejs.org)
- **Python**: `python --version` (3.12.x) — [Install](https://python.org)
- **Azure Functions Core Tools**: `func --version` (4.x) — `npm install -g azure-functions-core-tools@4`
- **SWA CLI**: `swa --version` — `npm install -g @azure/static-web-apps-cli`
- **Git**: `git --version`

### Azure account
- Active Azure subscription with Contributor access
- Ability to create resources: Cognitive Services, Cosmos DB, Storage, Key Vault, Static Web Apps, Function Apps

## Step 1: Clone and configure

```bash
git clone https://github.com/brandontyler/sermon.git
cd sermon
```

Create a `.env` file in the repo root:
```
ADMIN_KEY=<generate-a-random-key>
WEBSHARE_PROXY_USERNAME=<your-webshare-username>
WEBSHARE_PROXY_PASSWORD=<your-webshare-password>
```

Generate an admin key: `python3 -c "import secrets; print(secrets.token_urlsafe(32))"`

## Step 2: Azure login

```bash
az login
az account set --subscription "<your-subscription-id>"
```

Verify: `az account show --query "{name:name, id:id}" -o table`

## Step 3: Edit deploy.sh for your environment

Open `infra/deploy.sh` and update these variables if deploying to a different environment:

```bash
ENV="dev"                          # or "prod", "staging", etc.
RG="rg-sermon-rating-dev"         # resource group name
LOCATION="eastus2"                 # Azure region
```

**Important**: If you change `ENV`, all resource names change automatically (e.g., `psr-cosmos-dev` → `psr-cosmos-prod`).

**If you change the region**: Some Azure OpenAI models are only available in certain regions. Check model availability:
```bash
az cognitiveservices model list --location <your-region> --query "[?model.name=='gpt-5-nano'].model.name" -o tsv
```

## Step 4: Deploy infrastructure (Bicep)

```bash
./infra/deploy.sh infra
```

This creates all Azure resources:
- Resource group
- Cosmos DB (serverless) + database + 4 containers (sermons, feeds, churches, users)
- Storage account + sermon-audio blob container
- Azure OpenAI + 7 model deployments
- Azure AI Speech
- Azure Translator
- Key Vault + 10 secrets (populated server-side via Bicep)
- App Insights + Log Analytics workspace
- Function App (Python 3.12, Consumption plan)
- Static Web App (Standard tier)
- SWA linked backend (proxies /api/* to Function App)
- RBAC assignments (Function App managed identity → Key Vault, Storage, OpenAI, Speech, Cosmos)
- EasyAuth config (AllowAnonymous, SWA identity provider)

**Expected time**: 5-10 minutes

**After Bicep completes**, `deploy.sh infra` automatically deploys the backend code (because Bicep resets the Function App code).

### Verify infrastructure

```bash
# All resources created
az resource list -g <your-rg> --query "[].{name:name, type:type}" -o table

# Cosmos containers exist
az cosmosdb sql container list -a psr-cosmos-<env> -g <your-rg> -d psr --query "[].name" -o tsv

# OpenAI models deployed
az cognitiveservices account deployment list --name psr-openai-<env> -g <your-rg> --query "[].name" -o tsv

# Key Vault secrets populated
az keyvault secret list --vault-name psr-kv-<env>-001 --query "[].name" -o tsv

# Function App running
az functionapp show -n psr-functions-<env> -g <your-rg> --query "state" -o tsv
```

## Step 5: Verify backend functions

After deploy, wait 30-60 seconds for cold start, then:

```bash
# Should list ~45 functions
az functionapp function list -n psr-functions-<env> -g <your-rg> --query "[].name" -o tsv | wc -l

# Test the API
curl https://psr-functions-<env>.azurewebsites.net/api/sermons
```

### If functions list is empty

This is the most common issue. Check these in order:

1. **Key Vault access** — the Function App's managed identity needs Key Vault Secrets User role:
   ```bash
   # Check if RBAC is assigned
   az role assignment list --scope $(az keyvault show -n psr-kv-<env>-001 -g <your-rg> --query id -o tsv) --query "[?principalName != ''].{role:roleDefinitionName, principal:principalName}" -o table
   ```

2. **Key Vault references resolving** — check for errors in app settings:
   ```bash
   az functionapp config appsettings list -n psr-functions-<env> -g <your-rg> -o json | python3 -c "
   import json, sys
   for s in json.load(sys.stdin):
       if 'KeyVault' in str(s.get('value','')):
           print(f'{s[\"name\"]}: {s[\"value\"][:80]}')
   "
   ```
   If you see `SecretNotFound` or `Unauthorized`, the managed identity doesn't have access.

3. **Redeploy with func CLI** (bypasses Oryx remote build issues):
   ```bash
   cd api
   func azure functionapp publish psr-functions-<env> --python
   ```
   The `--python` flag is critical — it packages dependencies locally.

4. **Check runtime logs**:
   ```bash
   az webapp log tail -n psr-functions-<env> -g <your-rg>
   ```
   Look for `ImportError`, `ModuleNotFoundError`, or Key Vault errors.

5. **Verify FUNCTIONS_EXTENSION_VERSION**:
   ```bash
   az functionapp config appsettings list -n psr-functions-<env> -g <your-rg> --query "[?name=='FUNCTIONS_EXTENSION_VERSION'].value" -o tsv
   ```
   Must be `~4`.

## Step 6: Deploy frontend

```bash
./infra/deploy.sh frontend
```

This builds the Next.js app and deploys to SWA. `NEXT_PUBLIC_API_URL` is set to empty (frontend uses relative `/api/*` paths through the SWA proxy).

**Verify**: Open `https://<swa-default-hostname>` in a browser. The sermons page should load.

Get the SWA hostname:
```bash
az staticwebapp show -n psr-web-<env> -g <your-rg> --query "defaultHostname" -o tsv
```

## Step 7: Custom domains (optional)

### DNS setup (Porkbun, Cloudflare, etc.)
Add CNAME records pointing to the SWA default hostname:
- `howwas.church` → `<swa-hostname>`
- `www.howwas.church` → `<swa-hostname>`
- `demo.howwas.church` → `<swa-hostname>`

### Register in SWA
```bash
az staticwebapp hostname set -n psr-web-<env> -g <your-rg> --hostname howwas.church
az staticwebapp hostname set -n psr-web-<env> -g <your-rg> --hostname www.howwas.church
az staticwebapp hostname set -n psr-web-<env> -g <your-rg> --hostname demo.howwas.church
```

## Step 8: Admin access

### Invite admins (SWA role assignment)
```bash
# Generate invitation link
az staticwebapp users invite -n psr-web-<env> -g <your-rg> \
  --authentication-provider aad \
  --user-details "user@example.com" \
  --role admin \
  --invitation-expiration-in-hours 168
```

The user clicks the link, signs in with Microsoft, and gets the `admin` role.

## Step 9: Subscribe to RSS feeds (optional)

Go to `https://<your-domain>/admin/feeds` (requires admin login), add a podcast feed URL, and click Subscribe. The daily timer function polls for new episodes automatically.

## Ongoing deployments

| What changed | Command |
|---|---|
| Backend Python code | `./infra/deploy.sh backend` |
| Frontend code | `./infra/deploy.sh frontend` |
| Both | `./infra/deploy.sh code` |
| Infrastructure (Bicep) | `./infra/deploy.sh infra` (auto-redeploys backend) |
| Everything | `./infra/deploy.sh all` |

### Pre-deploy checklist
- [ ] `az account show` — correct subscription?
- [ ] `.env` file exists with ADMIN_KEY, WEBSHARE_PROXY_USERNAME, WEBSHARE_PROXY_PASSWORD
- [ ] `cd api && python3 -m pytest tests/` — all tests pass?
- [ ] `cd web && npx jest` — all tests pass?

### Post-deploy verification
```bash
# API responds
curl -s -o /dev/null -w "%{http_code}" https://<your-domain>/api/sermons

# Functions registered
az functionapp function list -n psr-functions-<env> -g <your-rg> --query "length(@)"

# EasyAuth correct (should be AllowAnonymous)
az rest --method get \
  --url "https://management.azure.com$(az functionapp show -n psr-functions-<env> -g <your-rg> --query id -o tsv)/config/authsettingsV2?api-version=2023-12-01" \
  --query "properties.globalValidation.unauthenticatedClientAction" -o tsv
```

## Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| Functions list empty | Key Vault access or bad deploy | See Step 5 troubleshooting |
| "Failed to load sermons" in browser | Frontend calling wrong URL | Verify `NEXT_PUBLIC_API_URL` is empty, redeploy frontend |
| 401 on API calls | EasyAuth set to RedirectToLoginPage | `deploy.sh` re-applies AllowAnonymous after link; redeploy infra |
| CORS errors on subdomain | Missing origin in CORS | CORS is `*` at platform level; check Python `_cors_origin()` |
| 413 on file upload | SWA proxy body size limit | Large files need direct Function App URL or chunked upload |
| Admin pages show "Unauthorized" | User doesn't have admin role | Re-invite with `az staticwebapp users invite` |

## Architecture reference

```
Browser → SWA (howwas.church) → /api/* proxy → Function App → Cosmos DB
                                                            → Blob Storage
                                                            → Azure OpenAI
                                                            → Azure AI Speech
                                                            → Key Vault (secrets)
```

- Frontend: Next.js static export on SWA Standard tier
- Backend: Python 3.12 Azure Functions (Consumption plan)
- Auth: SWA EasyAuth (Microsoft/Entra ID) + route rules in staticwebapp.config.json
- Secrets: Key Vault with managed identity RBAC (no connection strings in code)
- CORS: Platform wildcard `*`, Python validates `*.howwas.church` on responses
