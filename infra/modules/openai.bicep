// Azure OpenAI — S0 + 3 model deployments
param location string
param environment string
param modelVersions object

resource openai 'Microsoft.CognitiveServices/accounts@2024-10-01' = {
  name: 'psr-openai-${environment}'
  location: location
  kind: 'OpenAI'
  sku: { name: 'S0' }
  properties: {
    // No customSubDomainName — existing resource uses regional endpoint.
    // Key-based auth via Key Vault secrets works without a custom subdomain.
    publicNetworkAccess: 'Enabled'
  }
}

resource o4mini 'Microsoft.CognitiveServices/accounts/deployments@2024-10-01' = {
  parent: openai
  name: 'o4-mini'
  sku: { name: 'Standard', capacity: 80 }
  properties: {
    model: {
      format: 'OpenAI'
      name: 'o4-mini'
      version: modelVersions.o4mini
    }
  }
}

resource gpt41 'Microsoft.CognitiveServices/accounts/deployments@2024-10-01' = {
  parent: openai
  name: 'gpt-41'
  sku: { name: 'Standard', capacity: 50 }
  properties: {
    model: {
      format: 'OpenAI'
      name: 'gpt-4.1'
      version: modelVersions.gpt41
    }
  }
  dependsOn: [o4mini]
}

resource gpt41mini 'Microsoft.CognitiveServices/accounts/deployments@2024-10-01' = {
  parent: openai
  name: 'gpt-41-mini'
  sku: { name: 'Standard', capacity: 80 }
  properties: {
    model: {
      format: 'OpenAI'
      name: 'gpt-4.1-mini'
      version: modelVersions.gpt41mini
    }
  }
  dependsOn: [gpt41]
}

output id string = openai.id
output name string = openai.name
output endpoint string = openai.properties.endpoint
