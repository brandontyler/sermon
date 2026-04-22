// Static Web App — Standard tier (multi-tenant subdomains, custom auth)
param location string
param environment string

resource swa 'Microsoft.Web/staticSites@2023-12-01' = {
  name: 'psr-web-${environment}'
  location: location
  sku: { name: 'Standard', tier: 'Standard' }
  properties: {}
}

// --- Custom domains (DNS CNAME records must already exist on Porkbun) ---
// SWA validates domain ownership via the existing CNAME pointing to the default hostname.

resource domainApex 'Microsoft.Web/staticSites/customDomains@2023-12-01' = {
  parent: swa
  name: 'howwas.church'
  properties: {}
}

resource domainWww 'Microsoft.Web/staticSites/customDomains@2023-12-01' = {
  parent: swa
  name: 'www.howwas.church'
  properties: {}
}

resource domainDentonBible 'Microsoft.Web/staticSites/customDomains@2023-12-01' = {
  parent: swa
  name: 'dentonbible.howwas.church'
  properties: {}
}

resource domainDemo 'Microsoft.Web/staticSites/customDomains@2023-12-01' = {
  parent: swa
  name: 'demo.howwas.church'
  properties: {}
}

output id string = swa.id
output name string = swa.name
output defaultHostname string = swa.properties.defaultHostname
