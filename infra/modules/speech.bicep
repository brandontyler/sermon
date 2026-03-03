// AI Speech Service — F0 free tier (5 hrs/mo transcription)
param location string
param environment string

resource speech 'Microsoft.CognitiveServices/accounts@2024-10-01' = {
  name: 'psr-speech-${environment}'
  location: location
  kind: 'SpeechServices'
  sku: { name: 'F0' }
  properties: {
    publicNetworkAccess: 'Enabled'
  }
}

output id string = speech.id
output name string = speech.name
output endpoint string = speech.properties.endpoint
