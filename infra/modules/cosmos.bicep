// Cosmos DB — serverless NoSQL
param location string
param environment string

resource cosmos 'Microsoft.DocumentDB/databaseAccounts@2024-12-01-preview' = {
  name: 'psr-cosmos-${environment}'
  location: location
  kind: 'GlobalDocumentDB'
  properties: {
    databaseAccountOfferType: 'Standard'
    capabilities: [{ name: 'EnableServerless' }]
    locations: [{ locationName: location, failoverPriority: 0 }]
    consistencyPolicy: { defaultConsistencyLevel: 'Session' }
  }
}

resource database 'Microsoft.DocumentDB/databaseAccounts/sqlDatabases@2024-12-01-preview' = {
  parent: cosmos
  name: 'psr'
  properties: {
    resource: { id: 'psr' }
  }
}

// --- Containers (serverless — no throughput options) ---

resource sermons 'Microsoft.DocumentDB/databaseAccounts/sqlDatabases/containers@2024-12-01-preview' = {
  parent: database
  name: 'sermons'
  properties: {
    resource: {
      id: 'sermons'
      partitionKey: { paths: ['/id'], kind: 'Hash' }
    }
  }
}

resource feeds 'Microsoft.DocumentDB/databaseAccounts/sqlDatabases/containers@2024-12-01-preview' = {
  parent: database
  name: 'feeds'
  properties: {
    resource: {
      id: 'feeds'
      partitionKey: { paths: ['/id'], kind: 'Hash' }
    }
  }
}

resource churches 'Microsoft.DocumentDB/databaseAccounts/sqlDatabases/containers@2024-12-01-preview' = {
  parent: database
  name: 'churches'
  properties: {
    resource: {
      id: 'churches'
      partitionKey: { paths: ['/id'], kind: 'Hash' }
    }
  }
}

resource users 'Microsoft.DocumentDB/databaseAccounts/sqlDatabases/containers@2024-12-01-preview' = {
  parent: database
  name: 'users'
  properties: {
    resource: {
      id: 'users'
      partitionKey: { paths: ['/id'], kind: 'Hash' }
    }
  }
}

output id string = cosmos.id
output name string = cosmos.name
output endpoint string = cosmos.properties.documentEndpoint
