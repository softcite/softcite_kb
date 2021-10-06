// read the result object and return useful vals based on ES results
// returns an object that contains things like ["data"] and ["facets"]
var parseresultsElasticSearch = function (dataobj) {
    var resultobj = new Object();
    resultobj["records"] = new Array();
    resultobj["highlights"] = new Array();
    resultobj["scores"] = new Array();
    resultobj["ids"] = new Array();
    resultobj["start"] = "";
    resultobj["found"] = "";
    resultobj["took"] = "";
    resultobj["aggregations3"] = new Object();
    resultobj["aggregations"] = new Object();
    for (var item in dataobj.hits.hits) {
        resultobj["records"].push(dataobj.hits.hits[item].fields);
        resultobj["highlights"].push(dataobj.hits.hits[item].highlight);
        resultobj["scores"].push(dataobj.hits.hits[item]._score);
        resultobj["ids"].push(dataobj.hits.hits[item]._id);
        resultobj["start"] = "";
        resultobj["found"] = dataobj.hits.total;
        resultobj["took"] = dataobj.took;
    }
    for (var item in dataobj.aggregations) {
        var aggregationsobj = new Object();
        for (var thing in dataobj.aggregations[item]["buckets"]) {
            aggregationsobj[ dataobj.aggregations[item]["buckets"][thing]["key"] ] =
                    dataobj.aggregations[item]["buckets"][thing]["doc_count"];
        }
        resultobj["aggregations"][item] = aggregationsobj;
    }
    for (var item in dataobj.aggregations) {
        resultobj["aggregations3"][item] = dataobj.aggregations[item]["buckets"];
    }
    return resultobj;
};
