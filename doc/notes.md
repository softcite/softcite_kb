## Export the ArangoDB Knowledge Base DB

Exporting all the databses:

```console
arangodump --server.username root --all-databases true --output-directory "dump"
```

Exporting only the final KB database: 

```console
arangodump --server.username root --server.database kb --output-directory "dump"
```

