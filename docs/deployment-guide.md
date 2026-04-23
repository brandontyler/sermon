# PSR Deployment Guide

Complete checklist for deploying howwas.church to a new Azure subscription from scratch.
Written for both humans and coding agents.

## Step 0: Azure OpenAI Access (do this FIRST — takes 1-2 business days)

Azure OpenAI is a gated service. New subscriptions must be approved before deploying any models.

1. Apply at: https://aka.ms/oai/access
2. Wait for approval email (typically 1-2 business days)
3. **Do not proceed with Step 4 (Bicep deploy) until approved** — the OpenAI module will fail

You can complete Steps 1-3 while waiting.

## Prerequisites

### Local tools
| Tool | Check | Install |
|---|---|---|
| Azure CLI 2.60+ | `az --version` | https://learn.microsoft.com/en-us/cli/azure/install-azure-cli |
| Node.js 20+ | `node --version` | https://nodejs.org |
| Python 3.12.x | `python --version` | https://python.org |
| Azure Functions Core Tools v4 | `func --version` | `npm install -g azure-functions-core-tools@4` |
| SWA CLI | `swa --version` | `npm install -g @azure/static-web-apps-cli` |
| Git | `git --version` | https://git-scm.com |

### Azure account
- Active Azure subscription with Contributor access
- Azure OpenAI access approved (Step 0)

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

## Step 3: Choose your region

**Critical**: Not all Azure regions support all services. Choose carefully.

### Recommended regions (all services available)
- `eastus2` (our primary — all OpenAI models available)
- `eastus`
- `swedencentral`

### If you must use a different region
Azure OpenAI models are only available in specific regions. Check before deploying:
```bash
az cognitiveservices model list --location <your-region> --query "[?model.name=='o4-mini'].model.name" -o tsv
```

If your region doesn't have OpenAI models, you can deploy OpenAI in a supported region (e.g., `eastus2`) while keeping everything else in your preferred region. This requires making the OpenAI location a separate parameter in the Bicep.

### Resource name uniqueness
Azure requires globally unique names for: Storage accounts, Cosmos DB, Key Vault, Function Apps, Cognitive Services. Our Bicep uses `uniqueString(resourceGroup().id)` suffixes to handle this automatically. If you see name conflicts, the suffix ensures uniqueness per resource group.

## Step 4: Edit deploy.sh for your environment

Open `infra/deploy.sh` and update these variables:

```bash
ENV="dev"                          # or "prod", "staging", etc.
RG="rg-sermon-rating-dev"         # your resource group name
LOCATION="eastus2"                 # Azure region (see Step 3)
```

**If you change `ENV`**, all resource names change automatically.

## Step 5: Deploy infrastructure (Bicep)

```bash
./infra/deploy.sh infra
```

**On Windows (PowerShell)**, run the steps manually — see "Windows Deployment" section below.

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

After Bicep completes, `deploy.sh infra` automatically deploys the backend code (because Bicep resets the Function App code).

### Verify infrastructure

```bash
# All resources created
az resource list -g <your-rg> --query "[].{name:name, type:type}" -o table

# Cosmos containers exist
az cosmosdb sql container list -a <cosmos-name> -g <your-rg> -d psr --query "[].name" -o tsv

# OpenAI models deployed
az cognitiveservices account deployment list --name <openai-name> -g <your-rg> --query "[].name" -o tsv

# Function App running
az functionapp show -n <func-name> -g <your-rg> --query "state" -o tsv
```

## Step 6: Deploy backend (Function App)

If `deploy.sh infra` already deployed the backend, skip this. Otherwise:

```bash
./infra/deploy.sh backend
```

**Or manually with func CLI** (recommended for troubleshooting):
```bash
cd api
func azure functionapp publish <your-func-name> --python
```

The `--python` flag is **critical** — it packages dependencies locally and does a zip deploy. Without it, the remote Oryx build often fails silently on Consumption plan.

### Verify backend

Wait 30-60 seconds for cold start, then:

```bash
# Test the API directly
curl https://<your-func-name>.azurewebsites.net/api/sermons
```

Should return `[]` (empty array) with HTTP 200. This confirms:
- Function App started ✅
- Python loaded ✅
- Key Vault secrets resolved ✅
- Cosmos DB connected ✅

**Note**: `az functionapp function list` may show empty for several minutes after deploy. This is a known Azure metadata sync delay. If the curl test returns 200, the functions are working — ignore the empty list.

### If the API returns errors

Check these in order:

1. **Key Vault access** — Function App managed identity needs Key Vault Secrets User role:
   ```bash
   az role assignment list --scope $(az keyvault show -n <kv-name> -g <your-rg> --query id -o tsv) \
     --query "[].{role:roleDefinitionName, principal:principalName}" -o table
   ```

2. **Key Vault references resolving**:
   ```bash
   az functionapp config appsettings list -n <func-name> -g <your-rg> \
     --query "[?contains(value,'KeyVault')].{name:name, value:value}" -o table
   ```
   If you see `SecretNotFound` or `Unauthorized`, the managed identity doesn't have access.

3. **Check runtime logs**:
   ```bash
   az webapp log tail -n <func-name> -g <your-rg>
   ```
   Look for `ImportError`, `ModuleNotFoundError`, or Key Vault errors.

4. **Verify FUNCTIONS_EXTENSION_VERSION is `~4`**:
   ```bash
   az functionapp config appsettings list -n <func-name> -g <your-rg> \
     --query "[?name=='FUNCTIONS_EXTENSION_VERSION'].value" -o tsv
   ```

## Step 7: Deploy frontend

```bash
./infra/deploy.sh frontend
```

`NEXT_PUBLIC_API_URL` must be empty (frontend uses relative `/api/*` paths through the SWA proxy).

**Verify**: Get the SWA hostname and open in browser:
```bash
az staticwebapp show -n <swa-name> -g <your-rg> --query "defaultHostname" -o tsv
```

## Step 8: Custom domains (optional)

### DNS setup (Porkbun, Cloudflare, etc.)
Add CNAME records pointing to the SWA default hostname:
- `yourdomain.com` → `<swa-hostname>`
- `www.yourdomain.com` → `<swa-hostname>`

### Register in SWA
```bash
az staticwebapp hostname set -n <swa-name> -g <your-rg> --hostname yourdomain.com
```

## Step 9: Admin access

### Invite admins (SWA role assignment)
```bash
az staticwebapp users invite -n <swa-name> -g <your-rg> \
  --authentication-provider aad \
  --user-details "user@example.com" \
  --role admin \
  --invitation-expiration-in-hours 168
```

The user clicks the link, signs in with Microsoft, and gets the `admin` role.

## Windows Deployment

The `deploy.sh` script is bash. On Windows, run the steps manually in PowerShell:

### Infrastructure
```powershell
# Deploy Bicep
az deployment group create --resource-group <your-rg> `
  --template-file infra/main.bicep `
  --parameters infra/main.bicepparam `
  --parameters adminKey="<key>" webshareProxyUsername="<user>" webshareProxyPassword="<pass>"
```

### Backend
```powershell
cd api
.\.venv\Scripts\Activate.ps1   # activate Python venv
func azure functionapp publish <func-name> --python
```

### Frontend
```powershell
cd web
$env:NEXT_PUBLIC_API_URL = ""
npm install
npm run build
$token = az staticwebapp secrets list -n <swa-name> -g <your-rg> --query "properties.apiKey" -o tsv
swa deploy out --deployment-token $token --env production
```

### Link SWA backend (if not done by Bicep)
```powershell
$funcId = az functionapp show -n <func-name> -g <your-rg> --query id -o tsv
az staticwebapp backends link -n <swa-name> -g <your-rg> --backend-resource-id $funcId --backend-region <region>
```

## Ongoing Deployments

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

# EasyAuth correct (should be AllowAnonymous)
az rest --method get \
  --url "https://management.azure.com$(az functionapp show -n <func-name> -g <your-rg> --query id -o tsv)/config/authsettingsV2?api-version=2023-12-01" \
  --query "properties.globalValidation.unauthenticatedClientAction" -o tsv
```

## Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| OpenAI deploy fails | Subscription not approved | Apply at https://aka.ms/oai/access, wait 1-2 days |
| OpenAI deploy fails | Region doesn't have models | Use eastus2 or check `az cognitiveservices model list --location <region>` |
| Functions list empty after deploy | Normal Azure metadata delay | Wait 5-10 min; test with `curl` instead — if API returns 200, it's working |
| Functions list empty + API fails | Bad deploy or missing deps | Redeploy with `func azure functionapp publish <name> --python` |
| "Failed to load sermons" in browser | Frontend calling wrong URL | Verify `NEXT_PUBLIC_API_URL` is empty, redeploy frontend |
| 401 on API calls | EasyAuth set to RedirectToLoginPage | deploy.sh re-applies AllowAnonymous after link; redeploy infra |
| CORS errors on subdomain | Missing origin | CORS is `*` at platform level; check Python `_cors_origin()` |
| 413 on file upload | SWA proxy body size limit | Large files need direct Function App URL or chunked upload |
| Admin pages "Unauthorized" | User doesn't have admin role | Re-invite with `az staticwebapp users invite` |
| Resource name conflict | Globally unique names taken | Bicep uses `uniqueString()` suffix — change resource group name |
| Key Vault "Unauthorized" | Managed identity missing RBAC | Check RBAC assignments on Key Vault for the Function App principal |

## Architecture

```
Browser → SWA (howwas.church) → /api/* proxy → Function App → Cosmos DB
                                                            → Blob Storage
                                                            → Azure OpenAI
                                                            → Azure AI Speech
                                                            → Key Vault (secrets)
```

- **Frontend**: Next.js static export on SWA Standard tier
- **Backend**: Python 3.12 Azure Functions (Consumption plan)
- **Auth**: SWA EasyAuth (Microsoft/Entra ID) + route rules in staticwebapp.config.json
- **Secrets**: Key Vault with managed identity RBAC (no connection strings in code)
- **CORS**: Platform wildcard `*`, Python validates `*.howwas.church` on responses
- **Deploy**: `deploy.sh` wraps Bicep + func CLI + swa CLI. Re-applies EasyAuth after SWA backend link.
