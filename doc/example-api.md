This page illustrates some usage of the web API of the Software Knowledge Base. 

## Search queries

The search web service is actually a bridge to ElaticSearch. The Search queries have to be expressedi nthe ElasticSearch Query DSL, following the Software KB [indexing schema](https://github.com/softcite/softcite_kb/blob/master/software_kb/indexing/resources/kb_mappings.json).

For example searching for the term `STAR` in the field `software` (called `labels` in the field mapping, as a case insensitive field and ascii folding field version for software names):

```console
curl 'https://cloud.science-miner.com/software_kb/search/software-kb/_search?' -X POST -H 'Content-Type: application/json' -d'
{
    "fields": ["_id", "labels", "authors", "authors", "licenses", "collection", "programming_language_class", "organizations", "date", "number_mentions", "number_documents", "number_software", "descriptions", "summary"],
    "_source": false,
    "track_total_hits": true,
    "query": {
        "bool": {
            "should": [],
            "must": [{
                "query_string": {
                    "fields": ["labels"],
                    "query": "STAR",
                    "default_operator": "AND"
                }
            }],
            "must_not": []
        }
    },
    "sort": [{
        "number_documents": {
            "order": "desc"
        }
    }],
    "size": 12,
    "aggs": {
        "Entity": {
            "terms": {
                "field": "collection",
                "size": 60,
                "order": {
                    "_count": "desc"
                }
            }
        },
        "Author": {
            "terms": {
                "field": "authors_full",
                "size": 60,
                "order": {
                    "_count": "desc"
                }
            }
        },
        "Languages": {
            "terms": {
                "field": "programming_language_class",
                "size": 60,
                "order": {
                    "_count": "desc"
                }
            }
        }
    }
}'
```

Response with top 12 hits out of 192 hits:

```json
{
    "took": 24,
    "timed_out": false,
    "_shards": {
        "total": 1,
        "successful": 1,
        "skipped": 0,
        "failed": 0
    },
    "hits": {
        "total": {
            "value": 192,
            "relation": "eq"
        },
        "max_score": null,
        "hits": [{
            "_index": "software-kb",
            "_type": "_doc",
            "_id": "861fd4a20ab64fca8b33f0d6",
            "_score": null,
            "fields": {
                "summary": ["Functions to analyze neuronal spike trains from a single neuron or from several neurons recorded simultaneously."],
                "licenses": ["GPL-2 | GPL-3 [expanded from: GPL (≥ 2)]"],
                "number_documents": [829],
                "collection": ["software"],
                "programming_language_class": ["R"],
                "number_mentions": [1652],
                "descriptions": ["Spike Train Analysis with R"],
                "labels": ["STAR"],
                "authors": ["Christophe Pouzat"]
            },
            "sort": [829]
        }, {
            "_index": "software-kb",
            "_type": "_doc",
            "_id": "af78eae2b5d74d08a2b73376",
            "_score": null,
            "fields": {
                "number_documents": [57],
                "collection": ["software"],
                "number_mentions": [99],
                "labels": ["Questionnaire Star"]
            },
            "sort": [57]
        }, {
            "_index": "software-kb",
            "_type": "_doc",
            "_id": "0ef45e06ba9a4c4284d76088",
            "_score": null,
            "fields": {
                "number_documents": [41],
                "collection": ["software"],
                "number_mentions": [251],
                "labels": ["Star"]
            },
            "sort": [41]
        }, {
            "_index": "software-kb",
            "_type": "_doc",
            "_id": "8b528a9a8be24001a11cbe43",
            "_score": null,
            "fields": {
                "number_documents": [35],
                "collection": ["software"],
                "number_mentions": [41],
                "labels": ["STAR aligner"]
            },
            "sort": [35]
        }, {
            "_index": "software-kb",
            "_type": "_doc",
            "_id": "41f48da67b564c0e83599526",
            "_score": null,
            "fields": {
                "number_documents": [23],
                "collection": ["software"],
                "number_mentions": [24],
                "labels": ["DNA Star"]
            },
            "sort": [23]
        }, {
            "_index": "software-kb",
            "_type": "_doc",
            "_id": "ad5cda2d4c9e448bb9ea2174",
            "_score": null,
            "fields": {
                "number_documents": [17],
                "collection": ["software"],
                "number_mentions": [26],
                "labels": ["STAR-CD"]
            },
            "sort": [17]
        }, {
            "_index": "software-kb",
            "_type": "_doc",
            "_id": "b11e75c8aba1492db18a6edb",
            "_score": null,
            "fields": {
                "number_documents": [11],
                "collection": ["software"],
                "number_mentions": [11],
                "labels": ["STAR Aligner"]
            },
            "sort": [11]
        }, {
            "_index": "software-kb",
            "_type": "_doc",
            "_id": "7ac0685f56774fb4b2026192",
            "_score": null,
            "fields": {
                "number_documents": [8],
                "collection": ["software"],
                "number_mentions": [9],
                "labels": ["DNA STAR"]
            },
            "sort": [8]
        }, {
            "_index": "software-kb",
            "_type": "_doc",
            "_id": "1ae184b8f30f4b0e8d0019d3",
            "_score": null,
            "fields": {
                "number_documents": [7],
                "collection": ["software"],
                "number_mentions": [8],
                "labels": ["STAR e"]
            },
            "sort": [7]
        }, {
            "_index": "software-kb",
            "_type": "_doc",
            "_id": "01a1abcfff3a423bb271a4ad",
            "_score": null,
            "fields": {
                "number_documents": [6],
                "collection": ["software"],
                "number_mentions": [7],
                "labels": ["RNA-STAR"]
            },
            "sort": [6]
        }, {
            "_index": "software-kb",
            "_type": "_doc",
            "_id": "f3b8c031810f4f82a52865c2",
            "_score": null,
            "fields": {
                "number_documents": [6],
                "collection": ["software"],
                "number_mentions": [7],
                "labels": ["Star CCM+"]
            },
            "sort": [6]
        }, {
            "_index": "software-kb",
            "_type": "_doc",
            "_id": "7825b257ab8b480083f79fcf",
            "_score": null,
            "fields": {
                "number_documents": [6],
                "collection": ["software"],
                "number_mentions": [6],
                "labels": ["Survey Star"]
            },
            "sort": [6]
        }]
    },
    "aggregations": {
        "Entity": {
            "doc_count_error_upper_bound": 0,
            "sum_other_doc_count": 0,
            "buckets": [{
                "key": "software",
                "doc_count": 192
            }]
        },
        "Author": {
            "doc_count_error_upper_bound": 0,
            "sum_other_doc_count": 0,
            "buckets": [{
                "key": "Christophe Pouzat",
                "doc_count": 1
            }]
        },
        "Languages": {
            "doc_count_error_upper_bound": 0,
            "sum_other_doc_count": 0,
            "buckets": [{
                "key": "R",
                "doc_count": 1
            }]
        }
    }
}


```


## Retrieving full records

As software entities are searched, each hit comes with an `_id` key, which is the unique identifier for the software entity. This is similar when other entity type are searched. From this software identifier, it is possible to get the full software record as follow: 

```console
curl 'https://cloud.science-miner.com/software_kb/entities/software/861fd4a20ab64fca8b33f0d6' -H 'Accept: */*' 
```

Note if you prefer codemeta format (less complete) for example:

```console
curl 'https://cloud.science-miner.com/software_kb/entities/software/861fd4a20ab64fca8b33f0d6?format=codemeta' -H 'Accept: */*' 
```

Response with comple software entity record in the WikiData data model: 

```json
{
    "full_count": 1,
    "record": {
        "_key": "861fd4a20ab64fca8b33f0d6",
        "_id": "software/861fd4a20ab64fca8b33f0d6",
        "_rev": "_dViDoru---",
        "labels": "STAR",
        "descriptions": "Spike Train Analysis with R",
        "aliases": [],
        "type": "item",
        "claims": {
            "P31": [{
                "value": "Q7397",
                "datatype": "wikibase-item",
                "references": [{
                    "P248": {
                        "value": "Q2086703",
                        "datatype": "wikibase-item",
                        "count": 1
                    }
                }, {
                    "P248": {
                        "value": "Q2013",
                        "datatype": "wikibase-item",
                        "count": 1
                    }
                }, {
                    "P248": {
                        "value": "software-mentions",
                        "datatype": "string",
                        "count": 858
                    }
                }]
            }],
            "P277": [{
                "value": "Q206904",
                "datatype": "wikibase-item",
                "references": [{
                    "P248": {
                        "value": "Q2086703",
                        "datatype": "wikibase-item",
                        "count": 1
                    }
                }]
            }],
            "P275": [{
                "value": "GPL-2 | GPL-3 [expanded from: GPL (≥ 2)]",
                "datatype": "string",
                "references": [{
                    "P248": {
                        "value": "Q2086703",
                        "datatype": "wikibase-item",
                        "count": 1
                    }
                }]
            }],
            "P348": [{
                "value": "2.7",
                "datatype": "string",
                "references": [{
                    "P248": {
                        "value": "software-mentions",
                        "datatype": "string",
                        "count": 9
                    }
                }]
            }, {
                "value": "2.7.3a",
                "datatype": "string",
                "references": [{
                    "P248": {
                        "value": "software-mentions",
                        "datatype": "string",
                        "count": 55
                    }
                }]
            }, {
                "value": "2.6.1",
                "datatype": "string",
                "references": [{
                    "P248": {
                        "value": "software-mentions",
                        "datatype": "string",
                        "count": 8
                    }
                }]
            }, {
                "value": "2.5.2",
                "datatype": "string",
                "references": [{
                    "P248": {
                        "value": "software-mentions",
                        "datatype": "string",
                        "count": 24
                    }
                }]
            }, {
                "value": "2.7.2b",
                "datatype": "string",
                "references": [{
                    "P248": {
                        "value": "software-mentions",
                        "datatype": "string",
                        "count": 9
                    }
                }]
            }, {
                "value": "2.5.3a",
                "datatype": "string",
                "references": [{
                    "P248": {
                        "value": "software-mentions",
                        "datatype": "string",
                        "count": 54
                    }
                }]
            }, {
                "value": "2.5.0a",
                "datatype": "string",
                "references": [{
                    "P248": {
                        "value": "software-mentions",
                        "datatype": "string",
                        "count": 15
                    }
                }]
            }, {
                "value": "2.6.1d",
                "datatype": "string",
                "references": [{
                    "P248": {
                        "value": "software-mentions",
                        "datatype": "string",
                        "count": 21
                    }
                }]
            }],
            "P2078": [{
                "value": "https://cran.r-project.org/web/packages/STAR/STAR.pdf",
                "datatype": "url",
                "references": [{
                    "P248": {
                        "value": "Q2086703",
                        "datatype": "wikibase-item",
                        "count": 1
                    }
                }]
            }, {
                "value": "http://sites.google.com/site/spiketrainanalysiswithr",
                "datatype": "url",
                "references": [{
                    "P248": {
                        "value": "Q2086703",
                        "datatype": "wikibase-item",
                        "count": 1
                    }
                }]
            }],
            "P5565": [{
                "value": "STAR",
                "datatype": "external-id"
            }],
            "P178": [{
                "value": "Q7312427",
                "datatype": "wikibase-item",
                "references": [{
                    "P248": {
                        "value": "Q2013",
                        "datatype": "wikibase-item",
                        "count": 1
                    }
                }]
            }],
            "P856": [{
                "value": "http://www.renlearn.com/starreading/",
                "datatype": "url",
                "references": [{
                    "P248": {
                        "value": "Q2013",
                        "datatype": "wikibase-item",
                        "count": 1
                    }
                }]
            }],
            "P306": [{
                "value": "Q1406",
                "datatype": "wikibase-item",
                "references": [{
                    "P248": {
                        "value": "Q2013",
                        "datatype": "wikibase-item",
                        "count": 1
                    }
                }]
            }],
            "P123": [{
                "value": "Genomics Inc",
                "datatype": "string",
                "references": [{
                    "P248": {
                        "value": "software-mentions",
                        "datatype": "string",
                        "count": 1
                    }
                }]
            }, {
                "value": "Lexogen",
                "datatype": "string",
                "references": [{
                    "P248": {
                        "value": "software-mentions",
                        "datatype": "string",
                        "count": 1
                    }
                }]
            }, {
                "value": "Bioconductor",
                "datatype": "string",
                "references": [{
                    "P248": {
                        "value": "software-mentions",
                        "datatype": "string",
                        "count": 5
                    }
                }]
            }, {
                "value": "UCSC",
                "datatype": "string",
                "references": [{
                    "P248": {
                        "value": "software-mentions",
                        "datatype": "string",
                        "count": 2
                    }
                }]
            }, {
                "value": "Broad Institute",
                "datatype": "string",
                "references": [{
                    "P248": {
                        "value": "software-mentions",
                        "datatype": "string",
                        "count": 3
                    }
                }]
            }, {
                "value": "NCBI",
                "datatype": "string",
                "references": [{
                    "P248": {
                        "value": "software-mentions",
                        "datatype": "string",
                        "count": 5
                    }
                }]
            }],
            "P854": [{
                "value": "dna",
                "datatype": "url",
                "references": [{
                    "P248": {
                        "value": "software-mentions",
                        "datatype": "string",
                        "count": 1
                    }
                }]
            }, {
                "value": "https://www.gencodegenes.org",
                "datatype": "url",
                "references": [{
                    "P248": {
                        "value": "software-mentions",
                        "datatype": "string",
                        "count": 1
                    }
                }]
            }],
            "P767": [{
                "references": [{
                    "P248": {
                        "value": "Q2086703",
                        "datatype": "wikibase-item",
                        "count": 1
                    }
                }],
                "value": "persons/11fd786009e247068566ce52",
                "datatype": "internal-id"
            }]
        },
        "summary": "Functions to analyze neuronal spike trains from a single neuron or from several neurons recorded simultaneously."
    },
    "runtime": 0.011
}
```

## Retrieving software mentions

This will return software mentions grouped by documents, with ranking based on document number of mentions and using a usual paging cursor, for the software entity with identifier `861fd4a20ab64fca8b33f0d6`. 

```console
curl 'https://cloud.science-miner.com/software_kb/entities/software/861fd4a20ab64fca8b33f0d6/mentions?page_rank=0&page_size=10&ranker=group_by_document' -H 'Accept: */*' 
```
