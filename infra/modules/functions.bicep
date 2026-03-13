// Function App — Python 3.12, Linux, Consumption plan
param location string
param environment string
param storageName string
param appInsightsConnectionString string
param appInsightsInstrumentationKey string
param keyVaultUri string
param swaDefaultHostname string

// Reference existing storage account to build connection string locally (avoids listKeys in module outputs)
resource storageAccount 'Microsoft.Storage/storageAccounts@2023-05-01' existing = { name: storageName }
var storageConnectionString = 'DefaultEndpointsProtocol=https;AccountName=${storageAccount.name};AccountKey=${storageAccount.listKeys().keys[0].value};EndpointSuffix=${az.environment().suffixes.storage}'

resource plan 'Microsoft.Web/serverfarms@2023-12-01' = {
  name: 'psr-plan-${environment}'
  location: location
  sku: { name: 'Y1', tier: 'Dynamic' }
  kind: 'linux'
  properties: { reserved: true }
}

resource func 'Microsoft.Web/sites@2023-12-01' = {
  name: 'psr-functions-${environment}'
  location: location
  kind: 'functionapp,linux'
  identity: { type: 'SystemAssigned' }
  properties: {
    serverFarmId: plan.id
    httpsOnly: true
    siteConfig: {
      linuxFxVersion: 'Python|3.12'
      ftpsState: 'Disabled'
      cors: {
        allowedOrigins: [
          'https://${swaDefaultHostname}'
          'https://howwas.church'
        ]
      }
      appSettings: [
        // Runtime needs these at cold start — direct values, not Key Vault refs
        { name: 'AzureWebJobsStorage', value: storageConnectionString }
        { name: 'WEBSITE_CONTENTAZUREFILECONNECTIONSTRING', value: storageConnectionString }
        { name: 'WEBSITE_CONTENTSHARE', value: 'psr-functions-${environment}' }
        { name: 'FUNCTIONS_WORKER_RUNTIME', value: 'python' }
        { name: 'FUNCTIONS_EXTENSION_VERSION', value: '~4' }
        { name: 'APPLICATIONINSIGHTS_CONNECTION_STRING', value: appInsightsConnectionString }
        { name: 'APPINSIGHTS_INSTRUMENTATIONKEY', value: appInsightsInstrumentationKey }
        { name: 'WEBSITE_RUN_FROM_PACKAGE', value: '1' }
        // All others via Key Vault references
        { name: 'SPEECH_KEY', value: '@Microsoft.KeyVault(SecretUri=${keyVaultUri}secrets/speech-key/)' }
        { name: 'SPEECH_ENDPOINT', value: '@Microsoft.KeyVault(SecretUri=${keyVaultUri}secrets/speech-endpoint/)' }
        { name: 'OPENAI_KEY', value: '@Microsoft.KeyVault(SecretUri=${keyVaultUri}secrets/openai-key/)' }
        { name: 'OPENAI_ENDPOINT', value: '@Microsoft.KeyVault(SecretUri=${keyVaultUri}secrets/openai-endpoint/)' }
        { name: 'OPENAI_API_VERSION', value: '@Microsoft.KeyVault(SecretUri=${keyVaultUri}secrets/openai-api-version/)' }
        { name: 'COSMOS_CONNECTION_STRING', value: '@Microsoft.KeyVault(SecretUri=${keyVaultUri}secrets/cosmos-connection-string/)' }
        { name: 'STORAGE_CONNECTION_STRING', value: '@Microsoft.KeyVault(SecretUri=${keyVaultUri}secrets/storage-connection-string/)' }
      ]
    }
  }
}

output id string = func.id
output name string = func.name
output principalId string = func.identity.principalId
output defaultHostname string = func.properties.defaultHostName
