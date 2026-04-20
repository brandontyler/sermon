// Link Function App as SWA backend — proxies /api/* and injects x-ms-client-principal server-side
param environment string
param location string
param functionAppId string

resource swa 'Microsoft.Web/staticSites@2023-12-01' existing = {
  name: 'psr-web-${environment}'
}

resource linkedBackend 'Microsoft.Web/staticSites/linkedBackends@2023-12-01' = {
  parent: swa
  name: 'psr-functions-backend'
  properties: {
    backendResourceId: functionAppId
    region: location
  }
}
