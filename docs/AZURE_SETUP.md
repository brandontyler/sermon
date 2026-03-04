# Azure Setup

## Account

| Field | Value |
|-------|-------|
| **Subscription** | Visual Studio Enterprise |
| **Subscription ID** | 80b31d19-b663-4936-b8ee-93f7af5b1d27 |
| **Tenant ID** | f0d57f6c-d508-42b7-9ba9-8d00f8778f55 |
| **Account Type** | Personal (not company-managed) |
| **Monthly Credit** | $150 (VS Enterprise benefit) |
| **Role** | Owner |

> **Note:** Tyler's company VS Enterprise subscription had Azure credits blocked. This is a separate personal Azure account activated via [azure.microsoft.com/free](https://azure.microsoft.com/free) with VS Enterprise benefits. Budget-conscious — stick to consumption/serverless tiers.

## What Was Set Up (2026-02-27)

### 1. Azure CLI Installed

Corporate apt repos were broken, so we installed via Python venv:

```bash
python3 -m venv ~/.azure-cli-venv
~/.azure-cli-venv/bin/pip install azure-cli
sudo ln -sf ~/.azure-cli-venv/bin/az /usr/local/bin/az
```

Version: 2.83.0. Also added to `~/.bashrc` PATH.

### 2. Logged In

```bash
az login  # opens browser, sign in with personal MS account
```

To re-authenticate if session expires: `az login`

### 3. Resource Providers Registered

Azure requires you to "register" each service type before you can use it (like opting in to an AWS service API). Fresh subscriptions have nothing registered. We registered everything PSR needs across all phases. Registration is free — you only pay when you create actual resources.

**MVP (Phase 0):**
```bash
az provider register -n Microsoft.CognitiveServices    # Azure OpenAI + AI Speech
az provider register -n Microsoft.Storage              # Blob Storage (audio files)
az provider register -n Microsoft.Web                  # Azure Functions + Static Web Apps
az provider register -n Microsoft.DocumentDB           # Cosmos DB (metadata + results)
az provider register -n Microsoft.KeyVault             # Key Vault (secrets)
az provider register -n microsoft.insights             # Application Insights (monitoring)
az provider register -n Microsoft.OperationalInsights  # Log Analytics (App Insights dependency)
az provider register -n Microsoft.ManagedIdentity      # Managed identity (Functions → Key Vault auth)
```

**Phase 1 (Public Launch):**
```bash
az provider register -n Microsoft.AzureActiveDirectory # Azure AD B2C (user auth)
az provider register -n Microsoft.ServiceBus           # Message queue for processing jobs
az provider register -n Microsoft.EventGrid            # Event-driven triggers
az provider register -n Microsoft.Search               # AI Search (semantic search)
az provider register -n Microsoft.VideoIndexer         # Video processing (replaces retired Media Services)
```

**Phase 2 (Growth) + Supporting:**
```bash
az provider register -n Microsoft.Cdn                  # CDN / Front Door
az provider register -n Microsoft.Cache                # Redis Cache (leaderboards)
az provider register -n Microsoft.ApiManagement        # API gateway
az provider register -n Microsoft.Compute              # Sometimes needed by Functions internals
az provider register -n Microsoft.Network              # VNet, DNS
az provider register -n Microsoft.OperationsManagement # Monitoring solutions
az provider register -n Microsoft.AlertsManagement     # Alert rules
az provider register -n Microsoft.SignalRService       # Real-time processing status updates
az provider register -n Microsoft.CloudShell           # Browser-based terminal in Azure Portal
```

**Total: 22 providers registered.** Verify with:
```bash
az provider list --query "[?registrationState=='Registered'].namespace" -o tsv
```

> **Note:** Azure Media Services was retired in 2024. Video processing will use Microsoft.VideoIndexer instead.

### 4. Verified Permissions

- **Role:** Owner on the subscription (can create/delete anything)
- **Azure OpenAI:** Available (`az cognitiveservices account list-kinds` includes "OpenAI")
- **Resource creation:** Tested by creating and deleting a resource group

## Verification Commands

```bash
# Check login status
az account show -o table

# Check your role
az role assignment list --assignee $(az ad signed-in-user show --query id -o tsv) --query "[].roleDefinitionName" -o tsv

# Check all providers are registered
az provider list --query "[?namespace=='Microsoft.CognitiveServices' || namespace=='Microsoft.Storage' || namespace=='Microsoft.Web' || namespace=='Microsoft.DocumentDB' || namespace=='Microsoft.KeyVault' || namespace=='microsoft.insights'].{Provider:namespace, State:registrationState}" -o table

# Check Azure OpenAI availability
az cognitiveservices account list-kinds | grep OpenAI
```

### 5. Budget & Cost Alerts

$100/mo budget (leaves $50 buffer under the $150 credit). Email alerts go to your Azure login email.

| Threshold | Triggers At | You Get |
|-----------|-------------|---------|
| 50% | $50 spent | Email warning |
| 75% | $75 spent | Email warning |
| 100% | $100 spent | Email warning |

Budget name: `psr-monthly-budget`. Runs March 2026 – March 2027.

> **Important:** These are alerts only — Azure does NOT auto-stop spending. If you get the 100% alert, manually check what's running. The $50 buffer gives you time to react before hitting the $150 credit limit.

```bash
# Check budget status
az consumption budget show --budget-name psr-monthly-budget -o table
```

## What Was Created Manually (During POCs)

These resources were created via `az` CLI during POC development. The Bicep templates (infra/) recreate all of these from scratch — no manual steps needed for a fresh deployment.

| Resource | Name | Kind | SKU | Notes |
|----------|------|------|-----|-------|
| Resource Group | rg-sermon-rating-dev | — | — | eastus2 |
| AI Speech | psr-speech-dev | SpeechServices | F0 (free) | 5 hrs/mo free transcription |
| Azure OpenAI | psr-openai-dev | OpenAI | S0 | Regional endpoint (no custom subdomain) |
| OpenAI Deployment | o4-mini | o4-mini 2025-04-16 | Standard 80K TPM | Pass 1: Biblical Analysis |
| OpenAI Deployment | gpt-41 | gpt-4.1 2025-04-14 | Standard 50K TPM | Pass 2: Structure & Content |
| OpenAI Deployment | gpt-41-mini | gpt-4.1-mini 2025-04-14 | Standard 80K TPM | Pass 3: Delivery + Classification |

## Domain

| Field | Value |
|-------|-------|
| **Domain** | howwas.church |
| **Registrar** | Porkbun |
| **Purchased** | 2026-03-02 |
| **First Year** | $6.69 |
| **Renewal** | TBD (check Porkbun for .church renewal rate) |
| **Purpose** | Primary domain for PSR web app |

### DNS Setup (Completed 2026-03-04)

| Field | Value |
|-------|-------|
| **Static Web App** | `psr-web-dev` |
| **Default Hostname** | `gentle-ground-0713e880f.1.azurestaticapps.net` |
| **Porkbun API Access** | Enabled (keys in `.env`) |

#### Active DNS Records

| Type | Name | Target |
|------|------|--------|
| CNAME | `howwas.church` | `gentle-ground-0713e880f.1.azurestaticapps.net` |
| CNAME | `www.howwas.church` | `gentle-ground-0713e880f.1.azurestaticapps.net` |
| NS (x4) | `howwas.church` | Porkbun nameservers (do not modify) |

Both domains have Azure-managed SSL certificates (auto-provisioned, auto-renewed).

#### How It Was Set Up

1. **Porkbun API access** — enabled in Porkbun dashboard under domain settings. Required for programmatic DNS changes.
2. **Removed default records** — deleted the ALIAS and wildcard CNAME that pointed to `pixie.porkbun.com` (Porkbun parking page).
3. **Added CNAMEs** — root and `www` both point to the SWA default hostname via Porkbun API.
4. **Azure custom domain registration:**
   - `www.howwas.church` — standard CNAME validation (automatic).
   - `howwas.church` (apex) — required `--validation-method dns-txt-token`. Azure generates a token, you add it as a TXT record, Azure validates, then you delete the TXT record.
5. **SSL** — Azure auto-provisions and auto-renews managed certificates for both domains.

#### Gotchas

- **Apex domains can't use CNAME validation** on Azure Static Web Apps. You must use `dns-txt-token` validation: get the token via `az staticwebapp hostname show`, add a TXT record, wait for Azure to validate (can take 5-10 min), then clean up the TXT record.
- **Porkbun has Cloudflare proxy enabled by default** (`"cloudflare": "enabled"` in API responses). This doesn't break anything but means `dig CNAME howwas.church` returns empty — the CNAME is resolved behind Cloudflare's proxy as an A record. The actual CNAME is still there and working.
- **Validation timing** — `www` validated in ~2 minutes. The apex domain took ~15 minutes. Be patient.

#### Useful Commands

```bash
# Check domain status in Azure
az staticwebapp hostname list --name psr-web-dev --resource-group rg-sermon-rating-dev -o table

# Retrieve current DNS records via Porkbun API
source .env && curl -s -X POST https://api.porkbun.com/api/json/v3/dns/retrieve/howwas.church \
  -H "Content-Type: application/json" \
  -d "{\"apikey\": \"$PORKBUN_API_KEY\", \"secretapikey\": \"$PORKBUN_SECRET_KEY\"}" | python3 -m json.tool

# Add a DNS record (example: TXT record for domain verification)
source .env && curl -s -X POST https://api.porkbun.com/api/json/v3/dns/create/howwas.church \
  -H "Content-Type: application/json" \
  -d "{\"apikey\": \"$PORKBUN_API_KEY\", \"secretapikey\": \"$PORKBUN_SECRET_KEY\", \
       \"type\": \"TXT\", \"name\": \"\", \"content\": \"your-value\", \"ttl\": \"600\"}"

# Delete a DNS record by ID
source .env && curl -s -X POST https://api.porkbun.com/api/json/v3/dns/delete/howwas.church/RECORD_ID \
  -H "Content-Type: application/json" \
  -d "{\"apikey\": \"$PORKBUN_API_KEY\", \"secretapikey\": \"$PORKBUN_SECRET_KEY\"}"
```

#### Porkbun API Reference

- **Base URL:** `https://api.porkbun.com/api/json/v3`
- **Auth:** Every request body must include `apikey` and `secretapikey`
- **All requests are POST** (even reads/deletes)
- **Docs:** https://porkbun.com/api/json/v3/documentation

| Endpoint | Purpose |
|----------|---------|
| `/dns/retrieve/{domain}` | List all DNS records |
| `/dns/create/{domain}` | Add a record (body: type, name, content, ttl) |
| `/dns/delete/{domain}/{id}` | Delete a record by ID |
| `/dns/edit/{domain}/{id}` | Update a record by ID |

## What's Next

- Deploy full MVP infrastructure via Bicep templates (`infra/deploy.sh`)
