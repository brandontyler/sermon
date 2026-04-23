// Azure OpenAI — S0 + model deployments
param location string
param environment string
param modelVersions object

resource openai 'Microsoft.CognitiveServices/accounts@2024-10-01' = {
  name: 'psr-openai-${environment}'
  location: location
  kind: 'OpenAI'
  sku: { name: 'S0' }
  properties: {
    publicNetworkAccess: 'Enabled'
    disableLocalAuth: false  
  }
}

resource o4mini 'Microsoft.CognitiveServices/accounts/deployments@2024-10-01' = {
  parent: openai
  name: 'o4-mini'
  sku: { name: 'Standard', capacity: 80 }
  properties: {
    model: { format: 'OpenAI', name: 'o4-mini', version: modelVersions.o4mini }
raiPolicyName: 'Microsoft.Default'

  }
}

resource gpt41 'Microsoft.CognitiveServices/accounts/deployments@2024-10-01' = {
  parent: openai
  name: 'gpt-41'
  sku: { name: 'Standard', capacity: 50 }
  properties: {
    model: { format: 'OpenAI', name: 'gpt-4.1', version: modelVersions.gpt41 }
raiPolicyName: 'Microsoft.Default'
  }
  dependsOn: [o4mini]
}

resource gpt41mini 'Microsoft.CognitiveServices/accounts/deployments@2024-10-01' = {
  parent: openai
  name: 'gpt-41-mini'
  sku: { name: 'Standard', capacity: 80 }
  properties: {
    model: { format: 'OpenAI', name: 'gpt-4.1-mini', version: modelVersions.gpt41mini }
raiPolicyName: 'Microsoft.Default'
  }
  dependsOn: [gpt41]
}

resource gpt41nano 'Microsoft.CognitiveServices/accounts/deployments@2024-10-01' = {
  parent: openai
  name: 'gpt-41-nano'
  sku: { name: 'GlobalStandard', capacity: 50 }
  properties: {
    model: { format: 'OpenAI', name: 'gpt-4.1-nano', version: modelVersions.gpt41nano }
raiPolicyName: 'Microsoft.Default'
  }
  dependsOn: [gpt41mini]
}

resource gpt5mini 'Microsoft.CognitiveServices/accounts/deployments@2024-10-01' = {
  parent: openai
  name: 'gpt-5-mini'
  sku: { name: 'GlobalStandard', capacity: 50 }
  properties: {
    model: { format: 'OpenAI', name: 'gpt-5-mini', version: modelVersions.gpt5mini }
raiPolicyName: 'Microsoft.Default'
  }
  dependsOn: [gpt41nano]
}

resource gpt5nano 'Microsoft.CognitiveServices/accounts/deployments@2024-10-01' = {
  parent: openai
  name: 'gpt-5-nano'
  sku: { name: 'GlobalStandard', capacity: 50 }
  properties: {
    model: { format: 'OpenAI', name: 'gpt-5-nano', version: modelVersions.gpt5nano }
raiPolicyName: 'Microsoft.Default'
  }
  dependsOn: [gpt5mini]
}

resource gpt54 'Microsoft.CognitiveServices/accounts/deployments@2024-10-01' = {
  parent: openai
  name: 'gpt-54'
  sku: { name: 'GlobalStandard', capacity: 10 }
  properties: {
    model: { format: 'OpenAI', name: 'gpt-5.4', version: modelVersions.gpt54 }
    raiPolicyName: 'Microsoft.DefaultV2'
  }
  dependsOn: [gpt5nano]
}

output id string = openai.id
output name string = openai.name
output endpoint string = openai.properties.endpoint
