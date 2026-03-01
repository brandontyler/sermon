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

## What's Next

- Create resource group for PSR (`rg-sermon-rating-dev`)
- Deploy infrastructure via Bicep templates
