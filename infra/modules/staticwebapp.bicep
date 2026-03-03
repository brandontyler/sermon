// Static Web App — Free tier, Next.js
param location string
param environment string

resource swa 'Microsoft.Web/staticSites@2023-12-01' = {
  name: 'psr-web-${environment}'
  location: location
  sku: { name: 'Free', tier: 'Free' }
  properties: {}
}

output id string = swa.id
output name string = swa.name
output defaultHostname string = swa.properties.defaultHostname
