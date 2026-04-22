// Azure Translator — Text Translation
param location string
param environment string

resource translator 'Microsoft.CognitiveServices/accounts@2024-10-01' = {
  name: 'psr-translator-${environment}'
  location: location
  kind: 'TextTranslation'
  sku: { name: 'S1' }
  properties: {
    publicNetworkAccess: 'Enabled'
  }
}

output id string = translator.id
output name string = translator.name
