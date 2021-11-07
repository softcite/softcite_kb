(function ($) {
    $.fn.facetview = function(options) {

        var url_options = $.getUrlVars();
        var entity_id = url_options.id;
        var entity_type = url_options.type;
        if (!entity_type)
            entity_type = 'software'

        // async function
        async function fetchAsync(url) {
            // await response of fetch call
            let response = await fetch(url);
            let data = await response.json();
            return data;
        }

        async function getJsonFile(url) {
            let response = await fetch(url);
            let responsejson = await response.json();
            let str = JSON.stringify(responsejson);
            let jsonData = JSON.parse(str);
            return jsonData;
        };

        async function getJsonFileWithData(url, data) {
            let response = await fetch(
                url, { 
                    method: "POST", 
                    headers: {
                        "Accept": "application/json",
                        "Content-Type": "application/json"
                    },
                    body: data 
                }
            );
            let responsejson = await response.json();
            let str = JSON.stringify(responsejson);
            let jsonData = JSON.parse(str);
            return jsonData;
        };

        var showEntityMetadata = function(id) {
            // get json object for software
            getJsonFile(options.kb_service_host + "/entities/"+entity_type+"/"+id).then(softwareJson => {
                record = softwareJson["record"];

                metadata = '<div class="panel" style="margin-bottom:20!important; background-color:#ffffff; border: 1px;">';
                metadata += '<div style="padding: 20px; width:100%;">'
                metadata += '<p><table style="width:100%;"><tr><td>'

                metadata += '<strong>' + record["labels"] + "</strong>";
                if (record["descriptions"]) {
                    metadata += " - " + record["descriptions"] 
                }

                metadata += '</td><td align="right"><a target="_blank" style="color:#999999;" href="' + 
                            options.kb_service_host + "/entities/"+entity_type+"/" + id +'?format=simple">wikidata-simplified <i class="fa fa-file"></i></a>';

                metadata += '</td><td align="right"><a target="_blank" style="color:#999999;" href="' + 
                            options.kb_service_host + "/entities/"+entity_type+"/" + id +'">wikidata <i class="fa fa-file"></i></a>';
                
                metadata += '</td><td align="right"><a target="_blank" style="color:#999999;" href="' + 
                            options.kb_service_host + "/entities/"+entity_type+"/" + id +'?format=codemeta">codemeta <i class="fa fa-file"></i></a>';

                metadata += "</td></tr></table></p>"
                if (record["summary"]) {
                    var localHtml = wiki2html(record["summary"], "en");
                    metadata += localHtml;
                }
                metadata += '</div>';
                metadata += '</div>';

                // mention summary panel
                if (entity_type === 'software') {
                    metadata += '<div class="panel" style="margin-bottom:20!important; background-color:#ffffff; border: 1px;">';
                    metadata += '<div style="padding: 20px; width:100%;"><table><tr><td><strong>Mentions</strong></td><td>&nbsp;&nbsp;</td> '
                    metadata += '<td><div id="mention-summary"/></td>'
                    metadata += '</tr></table></div>';
                    metadata += '</div>';

                    const local_es_query_json = 
                        '{ "_source": false, "fields": ["number_mentions", "number_documents"], "query": { "terms": { "_id": [ "' + id + '" ] } } }';
                    const get_es_url = options.kb_service_host + "/search/software-kb/_search";
                    getJsonFileWithData(get_es_url, local_es_query_json).then(responseJson => {
                        if (responseJson && responseJson['hits'] && responseJson['hits']['hits'] && responseJson['hits']['hits'].length == 1) {
                            const es_entity_fields = responseJson['hits']['hits'][0]['fields']
                            
                            var localMentionData = '<a target="_blank" href="mentions.html?id=' + id + '&type=' + entity_type + '">';
                            localMentionData += es_entity_fields['number_mentions'] + ' mentions in ' + es_entity_fields['number_documents'] + ' documents';
                            localMentionData+= "</a>";

                            $("#mention-summary").empty();
                            $("#mention-summary").append(localMentionData);
                        }
                    });
                }

                if (record["claims"]) {
                    Object.keys(record["claims"]).forEach(function(key) {
                        if (key === "P18") {
                            // image
                            if (record["claims"][key].length > 0) {
                                metadata += '<div class="panel" style="margin-bottom:20!important; background-color:#ffffff; border: 1px;">';
                                metadata += '<div style="padding: 20px; width:100%;"><table><tr><td><strong>Gallery</strong></td><td>&nbsp;&nbsp;</td> '

                                // check wikipedia image based on wikimedia english page id
                                //if (record["claims"]["P460"])
                            
                                for(var index in record["claims"][key]) {
                                    //var imageUrl = "https://commons.wikimedia.org/wiki/File:" + record["claims"][key][0]["value"];
                                    var imageUrl = "https://commons.wikimedia.org/w/index.php?title=Special:Redirect/file/" + 
                                        record["claims"][key][index]["value"] + "&width=200";
                                    metadata += '<td><img src="' + imageUrl + '" width="200"/></td>';

                                }
                                metadata += '</tr></table></div>';
                                metadata += '</div>';
                            }
                        }
                    });
                }
                
                metadata += "</div></div>"
                $("#software-info").append(metadata);
            });
        }

        // for getting wikipedia page image
        const wikimediaURL_prefix = 'https://';
        const wikimediaURL_suffix = '.wikipedia.org/w/api.php?action=query&prop=pageimages&format=json&pithumbsize=200&pageids=';

        supportedLanguages = ['en']
        wikimediaUrls = {};
        for (var i = 0; i < supportedLanguages.length; i++) {
            var lang = supportedLanguages[i];
            wikimediaUrls[lang] = wikimediaURL_prefix + lang + wikimediaURL_suffix
        }

        //var imgCache = {};

        window.lookupWikiMediaImage = function (wikipedia, lang, pageIndex) {
            // first look in the local cache
            /*if (lang + wikipedia in imgCache) {
                var imgUrl = imgCache[lang + wikipedia];
                var document = (window.content) ? window.content.document : window.document;
                var spanNode = document.getElementById("img-" + wikipedia + "-" + pageIndex);
                spanNode.innerHTML = '<img src="' + imgUrl + '"/>';
            } else {*/
                // otherwise call the wikipedia API
                var theUrl = wikimediaUrls[lang] + wikipedia;

                // note: we could maybe use the en cross-lingual correspondence for getting more images in case of
                // non-English pages
                $.ajax({
                    url: theUrl,
                    jsonp: "callback",
                    dataType: "jsonp",
                    xhrFields: {withCredentials: true},
                    success: function (response) {
                        var document = (window.content) ? window.content.document : window.document;
                        var spanNode = document.getElementById("img-" + wikipedia + "-" + pageIndex);
                        if (response.query && spanNode) {
                            if (response.query.pages[wikipedia]) {
                                if (response.query.pages[wikipedia].thumbnail) {
                                    var imgUrl = response.query.pages[wikipedia].thumbnail.source;
                                    spanNode.innerHTML = '<img src="' + imgUrl + '"/>';
                                    // add to local cache for next time
                                    imgCache[lang + wikipedia] = imgUrl;
                                }
                            }
                        }
                    }
                });
            //}
        };

        showEntityMetadata(entity_id);
    }

})(jQuery);