// RBAC — Function App managed identity role assignments
// Cosmos DB data plane uses sqlRoleAssignments (not Microsoft.Authorization)
param functionAppPrincipalId string
param keyVaultName string
param storageName string
//param openaiName string
param speechName string
param cosmosName string

// --- Existing resource references ---
resource kv 'Microsoft.KeyVault/vaults@2023-07-01' existing = { name: keyVaultName }
resource storage 'Microsoft.Storage/storageAccounts@2023-05-01' existing = { name: storageName }
//resource openai 'Microsoft.CognitiveServices/accounts@2024-10-01' existing = { name: openaiName }
resource speech 'Microsoft.CognitiveServices/accounts@2024-10-01' existing = { name: speechName }
resource cosmos 'Microsoft.DocumentDB/databaseAccounts@2024-12-01-preview' existing = { name: cosmosName }

// Key Vault Secrets User
resource kvRole 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(kv.id, functionAppPrincipalId, '4633458b-17de-408a-b874-0445c86b69e6')
  scope: kv
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', '4633458b-17de-408a-b874-0445c86b69e6')
    principalId: functionAppPrincipalId
    principalType: 'ServicePrincipal'
  }
}

// Storage Blob Data Contributor
resource storageRole 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(storage.id, functionAppPrincipalId, 'ba92f5b4-2d11-453d-a403-e96b0029c9fe')
  scope: storage
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', 'ba92f5b4-2d11-453d-a403-e96b0029c9fe')
    principalId: functionAppPrincipalId
    principalType: 'ServicePrincipal'
  }
}

// Cognitive Services User (OpenAI)
//resource openaiRole 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
//  name: guid(openai.id, functionAppPrincipalId, 'a97b65f3-24c7-4388-baec-2e87135dc908')
//  scope: openai
//  properties: {
//    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', 'a97b65f3-24c7-4388-baec-2e87135dc908')
//    principalId: functionAppPrincipalId
//    principalType: 'ServicePrincipal'
//  }
//}

// Cognitive Services User (Speech)
resource speechRole 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(speech.id, functionAppPrincipalId, 'a97b65f3-24c7-4388-baec-2e87135dc908')
  scope: speech
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', 'a97b65f3-24c7-4388-baec-2e87135dc908')
    principalId: functionAppPrincipalId
    principalType: 'ServicePrincipal'
  }
}

// Cosmos DB Built-in Data Contributor (data plane — uses sqlRoleAssignments)
resource cosmosDataRole 'Microsoft.DocumentDB/databaseAccounts/sqlRoleAssignments@2024-12-01-preview' = {
  parent: cosmos
  name: guid('00000000-0000-0000-0000-000000000002', functionAppPrincipalId, cosmos.id)
  properties: {
    principalId: functionAppPrincipalId
    roleDefinitionId: '${cosmos.id}/sqlRoleDefinitions/00000000-0000-0000-0000-000000000002'
    scope: cosmos.id
  }
}
