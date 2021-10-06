var PublicationsByYearESQuery = function (params) {

    var qs = {};
    // set any facets
    qs['size'] = 0;
    if (params.topic)
        qs['query'] = {"filtered": {"filter": {"query": {"bool": {"must": [{"term": {"annotations.$standoff.$category.category": params.topic}
                                }
                            ]
                        }
                    }
                }, "query": {"match": {"organisations.organisationId": params.organisationID}
                }
            }
        }
    else
        qs['query'] = {"match": {"organisations.organisationId": params.organisationID}};

    qs['aggs'] = {
        "publication_date": {
            "date_histogram": {
                "field": "publication.date_printed", "interval": "year",
                "format": "yyyy-MM-dd"
            }
        }
    };
    var theUrl = JSON.stringify(qs);
    return theUrl;
};

var SubSructuresESQuery = function (params) {

    var qs = {};
    // set any facets
    qs['size'] = 10;
    qs['query'] = {"term": {"relations.organisationId": params.organisationID}};
    qs['sort'] = [
        {"docCount": {"order": "desc"}}
    ];
    var theUrl = JSON.stringify(qs);
    return theUrl;
};

var OrganisationIdByNameESQuery = function (params) {

    var qs = {};
    qs['query'] = {"match": {"names.name": params.orgName}};
    // set any facets
    qs['size'] = 1;
    var theUrl = JSON.stringify(qs);

    return theUrl;
};

var WikipideaCategoriesESQuery = function (params) {

    var qs = {};
    // set any facets
    qs['size'] = 10;

    if (params.topic)
        qs['query'] = {"filtered": {"filter": {"query": {"bool": {"must": [{"term": {"annotations.$standoff.$category.category": params.topic}
                                }
                            ]
                        }
                    }
                }, "query": {"match": {"organisations.organisationId": params.organisationID}
                }
            }
        }
    else
        qs['query'] = {"match": {"organisations.organisationId": params.organisationID}};

    qs['aggs'] = {"category": {"terms": {"field": "annotations.$standoff.$category.category", "size": 50}}};
    var theUrl = JSON.stringify(qs);
    return theUrl;
};

var KeytermsByYearESQuery = function (params) {

    var qs = {};
    // set any facets
    qs['size'] = 0;
    if (params.topic)
        qs['query'] = {"filtered": {"filter": {"query": {"bool": {"must": [{"term": {"annotations.$standoff.$category.category": params.topic}
                                }
                            ]
                        }
                    }
                }, "query": {"match": {"organisations.organisationId": params.organisationID}
                }
            }
        }
    else
        qs['query'] = {"match": {"organisations.organisationId": params.organisationID}};
    qs['aggs'] = {"keyterm": {"terms": {"field": "annotations.$standoff.$keyterm.preferredTerm", "size": 50},
            "aggs": {
                "publication_dates": {
                    "date_histogram": {
                        "field": "publication.date_printed", "interval": "year",
                        "format": "yyyy-MM-dd"
                    }
                }
            }

        }};
    var theUrl = JSON.stringify(qs);
    return theUrl;
};

var CoPublicationsByCountryESQuery = function (params) {

    var qs = {};
    if (params.topic)
        qs['query'] = {"filtered": {"filter": {"query": {"bool": {"must": [{"term": {"annotations.$standoff.$category.category": params.topic}
                                }
                            ]
                        }
                    }
                }, "query": {"match": {"organisations.organisationId": params.organisationID}
                }
            }
        }
    else
        qs['query'] = {"match": {"organisations.organisationId": params.organisationID}};
    // set any facets
    qs['size'] = 0;
    qs['aggs'] = {"country": {"terms": {"field": "organisations.address.country", "size": 100}}};

    var theUrl = JSON.stringify(qs);
    return theUrl;
};

var CollaborationsByYearESQuery = function (params) {

    var qs = {};
    if (params.topic)
        qs['query'] = {"filtered": {"filter": {"query": {"bool": {"must": [{"term": {"annotations.$standoff.$category.category": params.topic}
                                }
                            ]
                        }
                    }
                }, "query": {"match": {"organisations.organisationId": params.organisationID}
                }
            }
        }
    else
        qs['query'] = {"match": {"organisations.organisationId": params.organisationID}};
    // set any facets
    qs['size'] = 0;
    qs['aggs'] = {"orgs": {"terms": {"field": "organisations.organisationId", "size": 20},
            "aggs": {"publication_dates": {
                    "date_histogram": {
                        "field": "publication.date_printed", "interval": "year",
                        "format": "yyyy-MM-dd"
                    }}}

        }};




    var theUrl = JSON.stringify(qs);

    return theUrl;
};
var OrgNamesByOrgIdESQuery = function (ids) {

    var qs = {};
    qs['size'] = 20;
    qs['query'] = {"ids": {"values": ids}};
    // set any facets
    qs['fields'] = ["names.name"];




    var theUrl = JSON.stringify(qs);

    return theUrl;
};

var ConferencesByYearESQuery = function (params) {

    var qs = {};
    if (params.topic)
        qs['query'] = {"filtered": {"filter": {"query": {"bool": {"must": [{"term": {"annotations.$standoff.$category.category": params.topic}
                                }
                            ]
                        }
                    }
                }, "query": {"match": {"organisations.organisationId": params.organisationID}
                }
            }
        }
    else
        qs['query'] = {"match": {"organisations.organisationId": params.organisationID}};
    // set any facets
    qs['size'] = 0;
    qs['aggs'] = {"confs": {"terms": {"field": "publication.monograph.conference.title"},
            "aggs": {"publication_dates": {
                    "date_histogram": {
                        "field": "publication.date_printed", "interval": "year",
                        "format": "yyyy"
                    }}}

        }};

    var theUrl = JSON.stringify(qs);

    return theUrl;
};