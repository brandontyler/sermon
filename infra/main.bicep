// PSR MVP — Main Bicep orchestrator
// Deploys all Azure resources for howwas.church
// Usage: az deployment group create -g rg-sermon-rating-dev -f infra/main.bicep -p infra/main.bicepparam

targetScope = 'resourceGroup'

param location string
param environment string
param openaiModelVersions object

@secure()
param adminKey string
@secure()
param webshareProxyUsername string
@secure()
param webshareProxyPassword string

// --- Monitoring (needed by Functions) ---
module monitoring 'modules/monitoring.bicep' = {
  name: 'monitoring'
  params: { location: location, environment: environment }
}

// --- Storage (needed by Functions + pipeline) ---
module storage 'modules/storage.bicep' = {
  name: 'storage'
  params: { location: location, environment: environment }
}

// --- Cosmos DB ---
module cosmos 'modules/cosmos.bicep' = {
  name: 'cosmos'
  params: { location: location, environment: environment }
}

// --- AI Speech ---
module speech 'modules/speech.bicep' = {
  name: 'speech'
  params: { location: location, environment: environment }
}

// --- Azure OpenAI + model deployments ---
module openai 'modules/openai.bicep' = {
  name: 'openai'
  params: {
    location: location
    environment: environment
    modelVersions: openaiModelVersions
  }
}

// --- Key Vault (after services it reads keys from) ---
module keyvault 'modules/keyvault.bicep' = {
  name: 'keyvault'
  params: {
    location: location
    environment: environment
    tenantId: subscription().tenantId
    speechName: speech.outputs.name
    openaiName: openai.outputs.name
    cosmosName: cosmos.outputs.name
    storageName: storage.outputs.name
    adminKey: adminKey
    webshareProxyUsername: webshareProxyUsername
    webshareProxyPassword: webshareProxyPassword
  }
}

// --- Static Web App ---
module swa 'modules/staticwebapp.bicep' = {
  name: 'staticwebapp'
  params: { location: location, environment: environment }
}

// --- Function App ---
module functions 'modules/functions.bicep' = {
  name: 'functions'
  params: {
    location: location
    environment: environment
    storageName: storage.outputs.name
    appInsightsConnectionString: monitoring.outputs.appInsightsConnectionString
    appInsightsInstrumentationKey: monitoring.outputs.appInsightsInstrumentationKey
    keyVaultUri: keyvault.outputs.uri
    swaDefaultHostname: swa.outputs.defaultHostname
  }
}

// --- RBAC (after Function App creates managed identity) ---
module rbac 'modules/rbac.bicep' = {
  name: 'rbac'
  params: {
    functionAppPrincipalId: functions.outputs.principalId
    keyVaultName: keyvault.outputs.name
    storageName: storage.outputs.name
    openaiName: openai.outputs.name
    speechName: speech.outputs.name
    cosmosName: cosmos.outputs.name
  }
}

// --- Outputs for deploy.sh (no secrets — deploy.sh fetches keys via CLI) ---
output functionAppName string = functions.outputs.name
output swaDefaultHostname string = swa.outputs.defaultHostname
output keyVaultName string = keyvault.outputs.name
output speechName string = speech.outputs.name
output openaiName string = openai.outputs.name
output cosmosName string = cosmos.outputs.name
output storageName string = storage.outputs.name
