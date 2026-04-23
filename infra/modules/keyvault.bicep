// Key Vault — RBAC mode, secrets populated via Bicep listKeys() (server-side, never transit local machine)
param location string
param environment string
param tenantId string
param speechName string
//param openaiName string
param cosmosName string
param storageName string

@secure()
param adminKey string
@secure()
param webshareProxyUsername string
@secure()
param webshareProxyPassword string

var suffix = take(uniqueString(resourceGroup().id), 6)

resource kv 'Microsoft.KeyVault/vaults@2023-07-01' = {
  name: toLower('psrkv${environment}${suffix}')
  location: location
  properties: {
    sku: { family: 'A', name: 'standard' }
    tenantId: tenantId
    enableRbacAuthorization: true
    enableSoftDelete: true
    softDeleteRetentionInDays: 7
  }
}

// --- Reference existing resources to extract keys server-side ---
resource speech 'Microsoft.CognitiveServices/accounts@2024-10-01' existing = { name: speechName }
//resource openai 'Microsoft.CognitiveServices/accounts@2024-10-01' existing = { name: openaiName }
resource cosmos 'Microsoft.DocumentDB/databaseAccounts@2024-12-01-preview' existing = { name: cosmosName }
resource storage 'Microsoft.Storage/storageAccounts@2023-05-01' existing = { name: storageName }

// --- Secrets (all resolved server-side via ARM — keys never leave Azure) ---
resource speechKey 'Microsoft.KeyVault/vaults/secrets@2023-07-01' = {
  parent: kv
  name: 'speech-key'
  properties: { value: speech.listKeys().key1 }
}

resource speechEndpoint 'Microsoft.KeyVault/vaults/secrets@2023-07-01' = {
  parent: kv
  name: 'speech-endpoint'
  properties: { value: speech.properties.endpoint }
}

//resource openaiKey 'Microsoft.KeyVault/vaults/secrets@2023-07-01' = {
//  parent: kv
//  name: 'openai-key'
//  properties: { value: openai.listKeys().key1 }
//}

//resource openaiEndpoint 'Microsoft.KeyVault/vaults/secrets@2023-07-01' = {
//  parent: kv
//  name: 'openai-endpoint'
//  properties: { value: openai.properties.endpoint }
//}

//resource openaiApiVersion 'Microsoft.KeyVault/vaults/secrets@2023-07-01' = {
//  parent: kv
//  name: 'openai-api-version'
//  properties: { value: '2025-01-01-preview' }
//}

resource cosmosConnectionString 'Microsoft.KeyVault/vaults/secrets@2023-07-01' = {
  parent: kv
  name: 'cosmos-connection-string'
  properties: { value: cosmos.listConnectionStrings().connectionStrings[0].connectionString }
}

resource storageConnectionString 'Microsoft.KeyVault/vaults/secrets@2023-07-01' = {
  parent: kv
  name: 'storage-connection-string'
  properties: { value: 'DefaultEndpointsProtocol=https;AccountName=${storage.name};AccountKey=${storage.listKeys().keys[0].value};EndpointSuffix=${az.environment().suffixes.storage}' }
}

resource adminKeySecret 'Microsoft.KeyVault/vaults/secrets@2023-07-01' = {
  parent: kv
  name: 'admin-key'
  properties: { value: adminKey }
}

resource webshareUsernameSecret 'Microsoft.KeyVault/vaults/secrets@2023-07-01' = {
  parent: kv
  name: 'webshare-proxy-username'
  properties: { value: webshareProxyUsername }
}

resource websharePasswordSecret 'Microsoft.KeyVault/vaults/secrets@2023-07-01' = {
  parent: kv
  name: 'webshare-proxy-password'
  properties: { value: webshareProxyPassword }
}

output id string = kv.id
output name string = kv.name
output uri string = kv.properties.vaultUri
