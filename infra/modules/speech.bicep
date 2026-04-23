// AI Speech Service — S0 pay-as-you-go ($1/audio hour, $0 at idle)
param location string
param environment string

var suffix = take(uniqueString(resourceGroup().id), 6)


resource speech 'Microsoft.CognitiveServices/accounts@2024-10-01' = {
  name: 'psr-speech-${environment}${suffix}'
  location: location
  kind: 'SpeechServices'
  sku: { name: 'S0' }
  properties: {
    publicNetworkAccess: 'Enabled'
    disableLocalAuth: false  
  }
}

output id string = speech.id
output name string = speech.name
output endpoint string = speech.properties.endpoint
