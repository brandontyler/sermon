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
trap 'echo "✗ Deploy failed at line $LINENO (exit $?)" >&2' ERR
SECONDS=0

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

  # Load secrets from .env for Bicep secure params
  if [ -f "${PROJECT_DIR}/.env" ]; then
    ADMIN_KEY=$(grep '^ADMIN_KEY=' "${PROJECT_DIR}/.env" | cut -d= -f2-)
    WS_USER=$(grep '^WEBSHARE_PROXY_USERNAME=' "${PROJECT_DIR}/.env" | cut -d= -f2-)
    WS_PASS=$(grep '^WEBSHARE_PROXY_PASSWORD=' "${PROJECT_DIR}/.env" | cut -d= -f2-)
  fi
  : "${ADMIN_KEY:?Missing ADMIN_KEY in .env}"
  : "${WS_USER:?Missing WEBSHARE_PROXY_USERNAME in .env}"
  : "${WS_PASS:?Missing WEBSHARE_PROXY_PASSWORD in .env}"

  echo "[·] Resource group..."
  az group create --name "$RG" --location "$LOCATION" -o none
  echo "    ✓ $RG"

  purge_soft_deletes

  echo "[·] Deploying Bicep..."
  az deployment group create \
    --resource-group "$RG" \
    --template-file "${SCRIPT_DIR}/main.bicep" \
    --parameters "${SCRIPT_DIR}/main.bicepparam" \
    --parameters adminKey="$ADMIN_KEY" webshareProxyUsername="$WS_USER" webshareProxyPassword="$WS_PASS" \
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

  echo "    ✓ Secrets populated via Bicep (server-side)"

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
    echo "    ✗ func CLI not found. Install: sudo npm install -g azure-functions-core-tools@4"
    exit 1
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
    echo "    ✗ swa CLI not found. Install: sudo npm install -g @azure/static-web-apps-cli"
    exit 1
  fi

  # Set API URL so the frontend knows where to send requests
  # SWA Free tier doesn't support linked backends — frontend calls Function App directly
  echo "[·] Resolving Function App URL..."
  FUNC_URL="https://$(az functionapp show -n "$FUNC_NAME" -g "$RG" --query defaultHostName -o tsv)"
  echo "    ✓ ${FUNC_URL}"
  export NEXT_PUBLIC_API_URL="$FUNC_URL"

  echo "[·] Building frontend..."
  (cd "${PROJECT_DIR}/web" && npm install --silent && npm run build 2>&1 | tail -3)

  echo "[·] Deploying to Static Web App..."
  local SWA_TOKEN
  SWA_TOKEN=$(az staticwebapp secrets list -n "$SWA_NAME" -g "$RG" --query "properties.apiKey" -o tsv)
  # Next.js static export outputs to out/
  (cd "${PROJECT_DIR}/web" && swa deploy out --deployment-token "$SWA_TOKEN" --env production 2>&1 | tail -5)
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
    az group wait --deleted --resource-group "$RG" --timeout 600 2>/dev/null || true
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
  echo "  Teardown complete — no traces remain. (${SECONDS}s)"
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
    echo "  ✓ Everything deployed! (${SECONDS}s)"
    echo "  https://howwas.church (once DNS is configured)"
    echo "═══════════════════════════════════════════════"
    echo ""
    ;;
  infra)
    deploy_infra
    echo ""
    echo "  ⚠ Bicep redeploy resets Function App code — auto-restoring backend..."
    deploy_backend
    echo ""
    echo "  ✓ Infrastructure ready + backend restored (${SECONDS}s)"
    echo ""
    ;;
  code)
    deploy_backend
    deploy_frontend
    echo ""
    echo "  ✓ Code deployed! (${SECONDS}s)"
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
