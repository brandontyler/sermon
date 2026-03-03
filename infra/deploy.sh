#!/usr/bin/env bash
# PSR — One script to rule them all.
#
# Usage:
#   ./infra/deploy.sh              Deploy everything (infra + code)
#   ./infra/deploy.sh infra        Infrastructure only (Bicep + Key Vault secrets)
#   ./infra/deploy.sh code         Code only (Function App + frontend)
#   ./infra/deploy.sh backend      Function App code only
#   ./infra/deploy.sh frontend     Frontend code only
#   ./infra/deploy.sh teardown     Destroy everything (requires second 'teardown' to confirm)
#   ./infra/deploy.sh status       Show what's deployed

set -euo pipefail

ENV="dev"
RG="rg-sermon-rating-dev"
LOCATION="eastus2"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
CMD="${1:-all}"

# Resource names (derived from env)
KV_NAME="psr-kv-${ENV}-001"
FUNC_NAME="psr-functions-${ENV}"
SWA_NAME="psr-web-${ENV}"
OPENAI_NAME="psr-openai-${ENV}"
SPEECH_NAME="psr-speech-${ENV}"
COSMOS_NAME="psr-cosmos-${ENV}"
STORAGE_NAME="psrstorage${ENV}"

# ─────────────────────────────────────────────
#  Helpers
# ─────────────────────────────────────────────

check_tools() {
  local missing=()
  command -v az >/dev/null || missing+=(az)
  command -v python3 >/dev/null || missing+=(python3)
  if [ ${#missing[@]} -gt 0 ]; then
    echo "✗ Missing required tools: ${missing[*]}"
    exit 1
  fi
}

check_login() {
  if ! az account show -o none 2>/dev/null; then
    echo "✗ Not logged in. Run: az login"
    exit 1
  fi
}

ensure_providers() {
  echo "[·] Checking resource providers..."
  local PROVIDERS=(
    Microsoft.CognitiveServices Microsoft.Storage Microsoft.Web
    Microsoft.DocumentDB Microsoft.KeyVault microsoft.insights
    Microsoft.OperationalInsights Microsoft.ManagedIdentity
  )
  local REGISTERED
  REGISTERED=$(az provider list --query "[?registrationState=='Registered'].namespace" -o tsv 2>/dev/null)
  local NEED_REG=()
  for p in "${PROVIDERS[@]}"; do
    if ! echo "$REGISTERED" | grep -qi "^${p}$"; then
      NEED_REG+=("$p")
    fi
  done
  if [ ${#NEED_REG[@]} -gt 0 ]; then
    echo "    Registering: ${NEED_REG[*]}"
    for p in "${NEED_REG[@]}"; do
      az provider register -n "$p" --wait 2>/dev/null &
    done
    wait
  fi
  echo "    ✓ All providers ready"
}

purge_soft_deletes() {
  echo "[·] Checking for soft-deleted resources..."
  # Key Vault
  if az keyvault list-deleted --query "[?name=='${KV_NAME}']" -o tsv 2>/dev/null | grep -q "${KV_NAME}"; then
    echo "    Purging Key Vault ${KV_NAME}..."
    az keyvault purge --name "${KV_NAME}" --location "$LOCATION" -o none
  fi
  # Cognitive Services
  for CS_NAME in "$OPENAI_NAME" "$SPEECH_NAME"; do
    if az cognitiveservices account list-deleted --query "[?name=='${CS_NAME}']" -o tsv 2>/dev/null | grep -q "${CS_NAME}"; then
      echo "    Purging Cognitive Services ${CS_NAME}..."
      az cognitiveservices account purge --name "${CS_NAME}" --resource-group "$RG" --location "$LOCATION" -o none
    fi
  done
  echo "    ✓ Clean"
}

wait_for_keyvault() {
  echo "    Waiting for Key Vault access..."
  for i in 1 2 3 4 5 6; do
    if az keyvault secret set --vault-name "$KV_NAME" --name deploy-test --value "ok" -o none 2>/dev/null; then
      az keyvault secret delete --vault-name "$KV_NAME" --name deploy-test -o none 2>/dev/null || true
      return 0
    fi
    [ "$i" -eq 6 ] && { echo "    ✗ Key Vault RBAC timed out after 90s. Re-run."; exit 1; }
    echo "    Attempt $i/6..."
    sleep 15
  done
}

parse_output() {
  echo "$DEPLOY_OUTPUT" | python3 -c "import sys,json; print(json.load(sys.stdin)['$1']['value'])"
}

# ─────────────────────────────────────────────
#  Infrastructure
# ─────────────────────────────────────────────

deploy_infra() {
  echo ""
  echo "═══ Infrastructure ═══"

  ensure_providers

  echo "[·] Resource group..."
  az group create --name "$RG" --location "$LOCATION" -o none
  echo "    ✓ $RG"

  purge_soft_deletes

  echo "[·] Deploying Bicep..."
  az deployment group create \
    --resource-group "$RG" \
    --template-file "${SCRIPT_DIR}/main.bicep" \
    --parameters "${SCRIPT_DIR}/main.bicepparam" \
    -o none
  echo "    ✓ Bicep complete"

  # Read outputs from the completed deployment
  DEPLOY_OUTPUT=$(az deployment group show -g "$RG" -n main --query 'properties.outputs' -o json)

  # Create Cosmos DB container (Bicep can't create serverless containers reliably)
  echo "[·] Ensuring Cosmos DB container..."
  if ! az cosmosdb sql container show -a "$COSMOS_NAME" -g "$RG" -d psr -n sermons -o none 2>/dev/null; then
    az cosmosdb sql container create -a "$COSMOS_NAME" -g "$RG" -d psr -n sermons --partition-key-path "/id" -o none
    echo "    ✓ Created sermons container"
  else
    echo "    ✓ Container exists"
  fi

  # Read actual SWA hostname from deployment output (auto-generated, can't predict)
  SWA_HOST=$(parse_output swaDefaultHostname)

  echo "[·] Populating Key Vault secrets..."
  # Grant deploying user access
  local DEPLOYER_OID
  DEPLOYER_OID=$(az ad signed-in-user show --query id -o tsv)
  local KV_ID
  KV_ID=$(az keyvault show --name "$KV_NAME" --query id -o tsv)
  az role assignment create \
    --role "Key Vault Secrets Officer" \
    --assignee-object-id "$DEPLOYER_OID" \
    --assignee-principal-type User \
    --scope "$KV_ID" \
    -o none 2>/dev/null || true

  wait_for_keyvault

  # Fetch and store secrets
  local SPEECH_KEY SPEECH_ENDPOINT OPENAI_KEY OPENAI_ENDPOINT COSMOS_CONN STORAGE_CONN
  SPEECH_KEY=$(az cognitiveservices account keys list -n "$SPEECH_NAME" -g "$RG" --query key1 -o tsv)
  SPEECH_ENDPOINT=$(az cognitiveservices account show -n "$SPEECH_NAME" -g "$RG" --query properties.endpoint -o tsv)
  OPENAI_KEY=$(az cognitiveservices account keys list -n "$OPENAI_NAME" -g "$RG" --query key1 -o tsv)
  OPENAI_ENDPOINT=$(az cognitiveservices account show -n "$OPENAI_NAME" -g "$RG" --query properties.endpoint -o tsv)
  COSMOS_CONN=$(az cosmosdb keys list -n "$COSMOS_NAME" -g "$RG" --type connection-strings --query "connectionStrings[0].connectionString" -o tsv)
  STORAGE_CONN=$(az storage account show-connection-string -n "$STORAGE_NAME" -g "$RG" --query connectionString -o tsv)

  az keyvault secret set --vault-name "$KV_NAME" --name speech-key --value "$SPEECH_KEY" -o none
  az keyvault secret set --vault-name "$KV_NAME" --name speech-endpoint --value "$SPEECH_ENDPOINT" -o none
  az keyvault secret set --vault-name "$KV_NAME" --name openai-key --value "$OPENAI_KEY" -o none
  az keyvault secret set --vault-name "$KV_NAME" --name openai-endpoint --value "$OPENAI_ENDPOINT" -o none
  az keyvault secret set --vault-name "$KV_NAME" --name openai-api-version --value "2025-01-01-preview" -o none
  az keyvault secret set --vault-name "$KV_NAME" --name cosmos-connection-string --value "$COSMOS_CONN" -o none
  az keyvault secret set --vault-name "$KV_NAME" --name storage-connection-string --value "$STORAGE_CONN" -o none
  echo "    ✓ 7 secrets stored"

  # Link SWA backend to Function App (proxies /api/* — frontend just calls /api/sermons)
  echo "[·] Linking Static Web App backend..."
  local FUNC_ID
  FUNC_ID=$(az functionapp show -n "$FUNC_NAME" -g "$RG" --query id -o tsv 2>/dev/null)
  if [ -n "$FUNC_ID" ]; then
    az staticwebapp backends link -n "$SWA_NAME" -g "$RG" \
      --backend-resource-id "$FUNC_ID" \
      --backend-region "$LOCATION" \
      -o none 2>/dev/null || true
    echo "    ✓ Backend linked"
  fi
}

# ─────────────────────────────────────────────
#  Code Deployment
# ─────────────────────────────────────────────

deploy_backend() {
  echo ""
  echo "═══ Backend (Function App) ═══"

  # Check Function App exists
  if ! az functionapp show -n "$FUNC_NAME" -g "$RG" -o none 2>/dev/null; then
    echo "    ✗ Function App not found. Run: ./infra/deploy.sh infra"
    exit 1
  fi

  # Check func CLI
  if ! command -v func >/dev/null 2>/dev/null; then
    echo "    Installing Azure Functions Core Tools..."
    npm install -g azure-functions-core-tools@4 --unsafe-perm true 2>/dev/null
  fi

  echo "[·] Publishing Function App..."
  (cd "${PROJECT_DIR}/api" && func azure functionapp publish "$FUNC_NAME" --python 2>&1 | tail -5)
  echo "    ✓ Backend deployed"
}

deploy_frontend() {
  echo ""
  echo "═══ Frontend (Static Web App) ═══"

  if [ ! -d "${PROJECT_DIR}/web" ]; then
    echo "    ⚠ web/ directory not found — skipping frontend deploy"
    return 0
  fi

  # Check swa CLI
  if ! command -v swa >/dev/null 2>/dev/null; then
    echo "    Installing SWA CLI..."
    npm install -g @azure/static-web-apps-cli 2>/dev/null
  fi

  echo "[·] Building frontend..."
  (cd "${PROJECT_DIR}/web" && npm install --silent && npm run build 2>&1 | tail -3)

  echo "[·] Deploying to Static Web App..."
  local SWA_TOKEN
  SWA_TOKEN=$(az staticwebapp secrets list -n "$SWA_NAME" -g "$RG" --query "properties.apiKey" -o tsv)
  # Next.js hybrid mode: SWA CLI auto-detects .next directory
  (cd "${PROJECT_DIR}/web" && swa deploy .next --deployment-token "$SWA_TOKEN" --env production 2>&1 | tail -5)
  echo "    ✓ Frontend deployed"
}

# ─────────────────────────────────────────────
#  Teardown
# ─────────────────────────────────────────────

do_teardown() {
  echo ""
  echo "═══ Teardown ═══"
  echo ""
  echo "This will DELETE everything:"
  echo "  - All Azure resources in $RG"
  echo "  - All sermon data in Cosmos DB"
  echo "  - All uploaded audio in Blob Storage"
  echo ""

  # Require double confirmation
  if [ "${2:-}" != "teardown" ]; then
    echo "Type the command twice to confirm:"
    echo "  ./infra/deploy.sh teardown teardown"
    exit 0
  fi

  echo "[·] Deleting resource group..."
  if az group exists --name "$RG" -o tsv 2>/dev/null | grep -qi true; then
    az group delete --name "$RG" --yes --no-wait -o none
    echo "    Waiting (~2-5 min)..."
    az group wait --deleted --resource-group "$RG" 2>/dev/null || true
    echo "    ✓ Resource group deleted"
  else
    echo "    Already gone"
  fi

  echo "[·] Purging soft-deleted resources..."
  if az keyvault list-deleted --query "[?name=='${KV_NAME}']" -o tsv 2>/dev/null | grep -q "${KV_NAME}"; then
    az keyvault purge --name "$KV_NAME" --location "$LOCATION" -o none
    echo "    ✓ Purged Key Vault"
  fi
  for CS_NAME in "$OPENAI_NAME" "$SPEECH_NAME"; do
    if az cognitiveservices account list-deleted --query "[?name=='${CS_NAME}']" -o tsv 2>/dev/null | grep -q "${CS_NAME}"; then
      az cognitiveservices account purge --name "${CS_NAME}" --resource-group "$RG" --location "$LOCATION" -o none
      echo "    ✓ Purged ${CS_NAME}"
    fi
  done

  echo ""
  echo "═══════════════════════════════════════════════"
  echo "  Teardown complete — no traces remain."
  echo "  To redeploy: ./infra/deploy.sh"
  echo "═══════════════════════════════════════════════"
}

# ─────────────────────────────────────────────
#  Status
# ─────────────────────────────────────────────

show_status() {
  echo ""
  echo "═══ PSR Deployment Status ═══"
  echo ""

  if ! az group exists --name "$RG" -o tsv 2>/dev/null | grep -qi true; then
    echo "  Resource group $RG does not exist. Nothing deployed."
    return 0
  fi

  echo "  Resource Group: $RG ($LOCATION)"
  echo ""
  az resource list -g "$RG" --query "[].{Name:name, Type:type, Kind:kind}" -o table 2>/dev/null
  echo ""

  # Function App status
  if az functionapp show -n "$FUNC_NAME" -g "$RG" -o none 2>/dev/null; then
    local STATE
    STATE=$(az functionapp show -n "$FUNC_NAME" -g "$RG" --query state -o tsv)
    echo "  Function App: $FUNC_NAME ($STATE)"
  fi

  # SWA hostname
  if az staticwebapp show -n "$SWA_NAME" -g "$RG" -o none 2>/dev/null; then
    local HOST
    HOST=$(az staticwebapp show -n "$SWA_NAME" -g "$RG" --query defaultHostname -o tsv)
    echo "  Static Web App: https://$HOST"
  fi

  echo ""
}

# ─────────────────────────────────────────────
#  Main
# ─────────────────────────────────────────────

echo ""
check_tools
check_login

case "$CMD" in
  all)
    deploy_infra
    deploy_backend
    deploy_frontend
    echo ""
    echo "═══════════════════════════════════════════════"
    echo "  ✓ Everything deployed!"
    echo "  https://howwas.church (once DNS is configured)"
    echo "═══════════════════════════════════════════════"
    echo ""
    ;;
  infra)
    deploy_infra
    echo ""
    echo "  ✓ Infrastructure ready. Deploy code with: ./infra/deploy.sh code"
    echo ""
    ;;
  code)
    deploy_backend
    deploy_frontend
    echo ""
    echo "  ✓ Code deployed!"
    echo ""
    ;;
  backend)
    deploy_backend
    ;;
  frontend)
    deploy_frontend
    ;;
  teardown)
    do_teardown "$@"
    ;;
  status)
    show_status
    ;;
  *)
    echo "Usage: ./infra/deploy.sh [all|infra|code|backend|frontend|teardown|status]"
    echo ""
    echo "  all        Deploy everything — infra + backend + frontend (default)"
    echo "  infra      Infrastructure only (Bicep + Key Vault secrets)"
    echo "  code       Code only (backend + frontend)"
    echo "  backend    Function App code only"
    echo "  frontend   Static Web App only"
    echo "  teardown   Destroy everything (requires: teardown teardown)"
    echo "  status     Show what's deployed"
    exit 1
    ;;
esac
