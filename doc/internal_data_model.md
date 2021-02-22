# Knowledge Base data model

The Internal knowledge base model is based on Wikidata, which has been chosen for its focus on representing statements (claims) and references about entities, a mechanism which handles well diverging, uncertain and conflicting points of view. In our implementation, the Wikidata model is at the same time simplified to facilitate its readability and its manipulation in the disambiguation process and extended to better accomodate probabilitic and scoring mechanisms. 

Some relations corresponding to specific properties are stored as edge collections via an ArangoDB Graph for the purpose of exploiting graph algorithms such as pagerank, single-source shortest path, subgraph matching, community hub, etc. ArangoDB Graph is thus used to capture part of the overall Wikidata "graph" relevant for our requeriments. As a property graph, it maintains computational efficiency, predictive processing time and the availability of useful graph traversal algoritms for our use cases.

Considering a more comprehensive graph structure, or approximating an RDF graph for instance would limit the possibility to exploit the graph with respect to standard graph algorithms: SPARQL only does sub-graph matching and RDF leads to too many self-joins to achieve scalability, acceptable and predictable computational processing time. As a contrast, requirements for entity disambiguation and recommendation focus on path queries, shortest path similarity and pagerank scoring. In addition RDF data model presents limits when representing references, qualified relations, contradicting facts and non-discrete knowledge - which are central to the scientific evergoing debate, making difficult the representation of the useful knowledge in scientific fields. 

Data corresponding to vertex collection are stored as serialized JSON (see [Wikidata JSON serialization](https://doc.wikimedia.org/Wikibase/master/php/md_docs_topics_json.html)) and thus relies on ArangoDB JSON native storage and processing. The selected list of properties relevant to graph processing is presented below.  

From this internal representation, data are then exported by the Knowledge Base API in two formats :

- codemeta 

- Wikidata standard JSON serialization format 

## Keeping track of source information 

Following the Wikidata schema, the different information coming from a particular source about a software are represented as claims. We exploit the list references associated to each claim for representing the source of the information (aka its provenance). We use the property "stated in" (`P248`) to introduce the origin of the atomic information, with value either as Wikidata item or string if the source is not represented in Wikidata. 

For example, the provenance of the following claim about the developer of a software is CRAN (`Q2086703`):


```json
"claims": {
    "P178": [
        {
            "id": "Q153844$40995A01-4DD7-4046-8DA0-4BA30A1E97FB",
            "references": [ 
                {
                    "P248": {
                        "value": {
                            "id": "Q2086703"
                        },
                        "datatype": "wikibase-item"
                    } 
                }
            ],
            "qualifiers": { ... },
            "value": {
                  "id": "Q1668008"
            },
            "datatype": "wikibase-item"
        }
    ]
}
```

In case the source has no Wikidata item, we use a string value, for instance if the same claim comes from rOpenSci metadata:

```json
"claims": {
    "P178": [
        {
            "id": "Q153844$40995A01-4DD7-4046-8DA0-4BA30A1E97FB",
            "references": [ 
                {
                    "P248": {
                        "value": "rOpenSci",
                        "datatype": "string"
                    } 
                }
            ],
            "qualifiers": { ... },
            "value": {
                  "id": "Q1668008"
            },
            "datatype": "wikibase-item"
        }
    ]
}
```



## Representing scholar mentions in context

In the case of a mention in a publication, extracted via text mining, we express the citation as a relation (edge property) using "quoted by" (`Q66204407`), relating a software and a document. The property is enriched with several property/values pairs in the associated qualifier list to further describe the mention: mention text context, PDF coordinates, etc. In this case the source information of the relation is the text mining software which has extracted the mention.


## Simplification of Wikidata schema

One of the issue with Wikidata is the systematic usage of item and property identifiers, obfuscating the representation. To make the data representation more readable and easier to work with, and given the nature of the research software information, we applied the following simplification to the original Wikidata data schema:

- Only English is considered, so all multilingual levels of information are removed. 

- Item and Property identifiers are replaced by canonical readable identifiers derived from the English label. A dedicated key/value map is present to recover the original Wikidata-style identifiers.

- As few data types are used as values, mostly implicit and given that they are built on similar pieces of information, `snak` are simplified as a simple `value` attribute:

* for wikibase item:

```json
"claims": {
    "P178": [
        {
            "id": "Q153844$40995A01-4DD7-4046-8DA0-4BA30A1E97FB",
            "references": [ ... ],
            "qualifiers": { ... },
            "value": {
                  "id": "Q1668008"
            },
            "datatype": "wikibase-item"
        }
    ]
}
```

* for time:

```json
"claims": {
    "P585": [
        {
            "id": "Q153844$ac709ba7-4387-a275-9174-d739b651c2b0",
            "references": [ ... ],
            "qualifiers": { ... },
            "value": {
              "time": "+2019-10-25T00:00:00Z"
            },
            "datatype": "time"
        }
    ]
}
```

The exported data in Wikidata format re-introduces the original JSON format, the simplification being entirely reversible. 

## Extension of Wikidata schema

We introduce the following additional data fields to better accomodate probabilistic and scoring information at the level of statements:

- Confidence score attached to every statements between 0 and 1, which can be interpretated as the likelyhood that the claim is currently correct with respect to the ;atest version of the software or package. This is a certainty score, which can be produced by different scoring methods, and the particular method used to produced it must be described in the qualifier field. 

To better represent usage statistics, we introduce an additional set of properties specific to this Knowledge Base. Usage statistics are a set of numerical information imported from the data source when available. They are specific to software entities and expressed as statements too, with the following additional properties:

- download: number of downloads of the software or library

- endorsement: number of user endorsemnents for the software or library, for instance number of "stars" on GitHub

- fork: total number of fork of the software or library

- committer: number of committers 

- commit: number of commits

These properties can apply globally for a software project or by version/release.

All these numerical information are primarily used by the Knowledge Base to support various data disambiguation, ranking and data discovery algorithms. 


## Properties as edge collection

Part of the relational dimension of the Wikidata model is used to build an ArangoDB graph representation. Some statements that we want to see explicitly as graph edges are selected based on their property: 



