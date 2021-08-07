# Knowledge Base data model

The Internal knowledge base model is based on Wikidata, which has been chosen for its focus on representing statements (claims) and references about entities, a mechanism which handles well diverging, uncertain and conflicting points of view. In our implementation, the Wikidata model is at the same time:
* simplified to facilitate its readability and its manipulation in the disambiguation process, and 
* extended to better accomodate probabilistic and scoring mechanisms and cover missing properties for our use case. 

Some relations corresponding to specific properties are stored as edge collections via an ArangoDB Graph for the purpose of exploiting graph algorithms such as pagerank, single-source shortest path, subgraph matching, community hub, etc. ArangoDB Graph is thus used to capture part of the overall Wikidata "graph" relevant for our requeriments. As a property graph, it maintains computational efficiency, predictive processing time and the availability of useful graph traversal algoritms for our use cases.

Considering a more comprehensive graph structure, or approximating an RDF graph for instance would limit the possibility to exploit the graph with respect to standard graph algorithms: SPARQL only does sub-graph matching and RDF leads to too many self-joins to achieve scalability, acceptable and predictable computational processing time. As a contrast, requirements for entity disambiguation and recommendation focus on path queries, shortest path similarity and pagerank scoring. In addition RDF data model presents limits when representing references, qualified relations, contradicting facts and non-discrete knowledge - which are central to the scientific evergoing debate, making difficult the representation of the useful knowledge in scientific fields. 

Overall, our knowledge base is assembled from various sources and uncertain statements/text mining extractions at scale, commonly contradicting, therefore we use a paradigm focusing on the description of statements about resources (with scoring and probabilistic interpretation) rather than a paradigm designed for describing resources (like RDF). In addition, we ensure a clear distinction between the data model and the computational models to process the data (data can feed various processing approaches, like graph, search engines, probabilistic kb, relation or noSQL database), in contrast to OWL/RDF and SPARQL which bind data to a particular data processing engine.

Data corresponding to a vertex collection are stored as serialized JSON (see [Wikidata JSON serialization](https://doc.wikimedia.org/Wikibase/master/php/md_docs_topics_json.html)) and thus relies on ArangoDB JSON native storage and processing. The selected list of properties relevant to graph processing is presented below.  

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

In the case of a mention in a publication, extracted via text mining, we express the citation as a relation (edge property) using "quotes work" (`P6166`), relating a document and a software. The property is enriched with several property/values pairs in the associated qualifier list to further describe the mention: mention text context, PDF coordinates, etc. In this case the source information of the relation is the text mining software which has extracted the mention.

Below, we represent a citation as anedgae relation from a document entity (citing) and a software entity (cited). The relation comes from an extracted mention with the following information: named mention (`P6166`), coordinates in the original PDF corresponding to the citing document (`P2677`, via qualifiers field) and context of citation (`P7081` with the context sentence as value). As explained above, the source of the relation is expressed in the reference field via the property `P248` (here `software-mentions` for the Softcite software mention recognizer). 


```json
{
  "claims": {
    "P6166": [
      {
        "value": "Basic Local Alignment Search Tool (BLAST)",
        "datatype": "string",
        "references": [
          {
            "P248": {
              "value": "software-mentions",
              "datatype": "string",
              "count": 1
            }
          }
        ],
        "qualifiers": [
          {
            "P2677": {
              "value": [
                {
                  "x": 220.096,
                  "h": 9.584000000000003,
                  "y": 218.636,
                  "p": 3,
                  "w": 192.22770000000003
                }
              ],
              "datatype": "string"
            }
          }
        ]
      }
    ],
    "P7081": [
      {
        "value": "Sequences were aligned by Molecular Evolutionary Genetic Analysis version 7.0 (MEGA7) [6] and a search of homologous sequences was performed using Basic Local Alignment Search Tool (BLAST) [7].",
        "datatype": "string",
        "references": [
          {
            "P248": {
              "value": "software-mentions",
              "datatype": "string",
              "count": 1
            }
          }
        ]
      }
    ]
  }
}
```


## Simplification of Wikidata schema

One of the issue with Wikidata is the systematic usage of item and property identifiers, obfuscating the representation. To make the data representation more readable and easier to work with, and given the nature of the research software information, we applied the following simplification to the original Wikidata data schema:

- Only English is considered, so all multilingual levels of information are removed. 

- As few data types are used as values, mostly implicit and given that they are built on similar pieces of information, `snak` are simplified as a simple `value` attribute:

- [WIP] Item and Property identifiers are replaced by canonical readable identifiers derived from the English label. A dedicated key/value map is present to recover the original Wikidata-style identifiers.

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

The exported data in Wikidata format re-introduces the original JSON format, the simplifications being entirely reversible. 

## Extension of Wikidata schema

We introduce the following additional data fields to better accomodate probabilistic and scoring information at the level of statements:

- `count`, associated to a source (in `references` under property `P248`). The `count` indicates the number of time the statement has been observed in the source. For instance, for the source `software-mentions` corresponding to the Softcite software mention recognizer, the `count` gives the number of time the statement has been extracted in the corpus of scientific publication.

- Confidence score attached to every statements with value in [0,1], which can be interpretated as the likelyhood that the claim is currently correct with respect to the latest version of the software or package. This is a certainty score, which can be produced by different scoring methods, and the particular method used to produced it must be described in the qualifier field. 

To better represent usage statistics, we introduce an additional set of properties specific to this Knowledge Base. Usage statistics are a set of numerical information imported from the data source when available. They are specific to software entities and expressed as statements too, with the following additional properties:

- download: number of downloads of the software or library

- endorsement: number of user endorsemnents for the software or library, for instance number of "stars" on GitHub

- fork: total number of fork of the software or library

- committer: number of committers 

- commit: number of commits

These properties can be applied globally for a software project or by version/release (version/release information are then expressed as `qualifiers`).

All these numerical information are primarily used by the Knowledge Base to support data disambiguation, ranking and data discovery algorithms. 


## Properties as edge collections

For convenience, in the ArangoDB implementation, the imported entities are currently grouped in five vertex collections (`documents`, `organizations`, `licenses`, `persons`, `software`) and relations are grouped in six edge collections (`actors`, `citations`, `copyrights`, `references`, `dependencies`, `funding`). A property graph is built on top of these vertex using the six edges.

The six types of edges correspond to the part of the relational information of the Wikidata model used to build an ArangoDB graph representation. The statements that we want to see explicitly as graph edges are selected based on their property. 

- `citations` correspond to citation context via inline mentions from whithin a document, they are expressed as edge relations between a document (citing) and either a document or a software (cited work). The edge include information about the citation context (coordinates, sentence context, ...).

- `actors` edges are used to represent relations between entities (software, document, etc.) and persons. This is used to represent authorship or other roles between a person and a work, excluding intellectual property information. 

- `funding` edges relate an organization and a software, indicating that the organization has contributed financially to the software. 

- `copyrights` edges represent all Intellectual Property information (so not just copyrights in principle), and relate a person or an organization (IP holder) with a software (the creative work).

- `dependencies` are edges relating two software, indicating a directed compile/build dependency

- `references` capture formal reference relation between software and documents or between documents. This is for instance the reference of an article in the software metadata, or a reference introduced by a paper when citing a software. When the reference is associated to a cited software, the software information is represented in the reference edge. 
