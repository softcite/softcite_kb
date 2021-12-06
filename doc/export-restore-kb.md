## Export the ArangoDB Knowledge Base DB

Exporting only the final KB database and the _naming_ database (the `root` username is given as example): 

```console
arangodump --server.username root --server.database kb --output-directory "dump-kb"
arangodump --server.username root --server.database naming --output-directory "dump-naming"
```

Only the final KB and naming DB are required to run the KB server and the KB frontend. 

Or exporting all the databases (the `root` username is given as example):

```console
arangodump --server.username root --all-databases true --output-directory "dump"
```

## Restore the ArangoDB Knowledge Base DB

Restoring only the final KB database (the `root` username is given as example): 

```console
arangorestore --server.username root --server.database kb --create-database true --input-directory "dump"
```

If needed, restoring all databases (the `root` username is given as example):

```console
arangorestore --server.username root --all-databases true --create-database true --input-directory "dump"
```

After restoring the KB, the search index need to be rebuilt:

```console
python3 software_kb/indexing/kb_es_indexing.py --config my_config.yaml --reset
```
