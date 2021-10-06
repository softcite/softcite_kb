var PublicationsByYearESQuery = function () {

    var qs = {};

    // set any facets
    qs['size'] = 0;
    qs['query'] = {"match": {"authors.personId": authID}};
    qs['aggs'] = {
        "publication_date": {
                    "date_histogram": {"field": "publication.date_printed", "interval": "year",
                        "format": "yyyy-MM-dd"}
        }
    };

    var theUrl = JSON.stringify(qs);
    return theUrl;
};

var WikipediaCategoriesESQuery = function () {

    var qs = {};
    // set any facets
    qs['size'] = 10;
    qs['query'] = {"match": {"authors.personId": authID}};
    qs['aggs'] = {"category": {"terms": {"field": "annotations.$standoff.$category.category", "size": 20}}};
    var theUrl = JSON.stringify(qs);
    return theUrl;
};

var CoPublicationsByCountryESQuery = function () {

    var qs = {};
    qs['query'] = {"match": {"authors.personId": authID}};
    // set any facets
    qs['aggs'] = {"country": {"terms": {"field": "organisations.address.country", "size": 50}}};

    var theUrl = JSON.stringify(qs);

    return theUrl;
};

var CoAuthorsByYearESQuery = function () {

    var qs = {};

    // set any facets
    qs['size'] = 0;
//    if (params.topic)
//        qs['query'] = {"filtered": {"filter": {"query": {"bool": {"must": [{"term": {"annotations.$standoff.$category.category": params.topic}
//                                }
//                            ]
//                        }
//                    }
//                }, "query": {"match": {"organisations.organisationId": params.organisationID}
//                }
//            }
//        }
//    else
    qs['query'] = {"match": {"authors.personId": authID}};

    qs['aggs'] = {"publication_dates": {
            "date_histogram": {
                "field": "publication.date_printed", "interval": "year",
                "format": "yyyy-MM-dd"
            },
            "aggs": {
                "author": {"terms": {"field": "authors.personId", "size": 20}
                }
            }

        }};

    var theUrl = JSON.stringify(qs);

    return theUrl;
};

var PersonNamesByPersonId = function (ids) {

    var qs = {};
    qs['size'] = 250;
    qs['query'] = {"ids": {"values": ids}};
    // set any facets
    qs['fields'] = ["names.fullname"];
    var theUrl = JSON.stringify(qs);

    return theUrl;
};

var KeytermsByYearESQuery = function () {

    var qs = {};

    // set any facets
    qs['size'] = 0;
    qs['query'] = {"match": {"authors.personId": authID}};

    qs['aggs'] = {
        "keyterms": {"terms": {"field": "annotations.$standoff.$keyterm.preferredTerm", "size": 20}
            ,

            "aggs": {
                "publication_dates": {
                    "date_histogram": {
                        "field": "publication.date_printed", "interval": "year",
                        "format": "yyyy-MM-dd"
                    }}
            }

        }};

    var theUrl = JSON.stringify(qs);
    return theUrl;
};

var PublicationsByTopicESQuery = function () {

    var qs = {};

    // set any facets
    qs['size'] = 0; 
    
    qs['query'] = {"match": {"authors.personId": authID}};
    qs['aggs'] = {"topic":{"terms":{"field":"annotations.$standoff.$nerd.preferredTerm", "size": 6},
   "aggs": {
    "authors": {
     "terms": {
      "field": "authors.personId"
     }
    }
   }}};
    
    var theUrl = JSON.stringify(qs);

    return theUrl;
};