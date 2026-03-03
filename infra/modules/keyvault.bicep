// Key Vault — RBAC mode, secrets populated by deploy.sh
param location string
param environment string
param tenantId string

resource kv 'Microsoft.KeyVault/vaults@2023-07-01' = {
  name: 'psr-kv-${environment}-001'
  location: location
  properties: {
    sku: { family: 'A', name: 'standard' }
    tenantId: tenantId
    enableRbacAuthorization: true
    enableSoftDelete: true
    softDeleteRetentionInDays: 7
  }
}

output id string = kv.id
output name string = kv.name
output uri string = kv.properties.vaultUri
