using 'main.bicep'

param location = 'eastus2'
param environment = 'dev'
param openaiModelVersions = {
  o4mini: '2025-04-16'
  gpt41: '2025-04-14'
  gpt41mini: '2025-04-14'
}
