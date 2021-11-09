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

        // note: this is a basic encoding, for something comprehensive, use the he library (https://github.com/mathiasbynens/he)
        var encodedStr = function(rawStr) {
            return rawStr.replace(/[\u00A0-\u9999<>\&]/g, 
                function(i) {
                    return '&#'+i.charCodeAt(0)+';';
                });
        }

        var showEntityMetadata = function(id) {
            // get json object for software
            getJsonFile(options.kb_service_host + "/entities/"+entity_type+"/"+id).then(softwareJson => {
                record = softwareJson["record"];

                metadata = '<div class="panel" style="margin-bottom:20!important; background-color:#ffffff; border: 1px;">';
                metadata += '<div style="padding: 20px; width:100%;">'
                metadata += '<p><table style="width:100%;"><tr><td>'

                metadata += '<strong>' + encodedStr(record["labels"]) + "</strong>";
                if (record["descriptions"]) {
                    metadata += " - " + encodedStr(record["descriptions"]) 
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

                $("#software-info").append(metadata);

                // mention summary panel
                if (entity_type === 'software') {
                    metadata = '<div class="panel" style="margin-bottom:20!important; background-color:#ffffff; border: 1px;">';
                    metadata += '<div style="padding: 20px; width:100%;"><table width="100%">'+
                    '<tr><td><div style="width:60px;overflow: hidden;"><strong>Mentions</strong></div></td><td>&nbsp;&nbsp;</td> '
                    metadata += '<td><div id="mention-summary"/></td><td><div id="timeline"/></td>'+
                    '<td> <div style="width:100px;overflow: hidden;" id="info-timeline"/></td></tr></table></div>'
                    metadata += '</div>';

                    const local_es_query_json = 
                        '{ "_source": false, "fields": ["number_mentions", "number_documents", "timeline.key", "timeline.doc_count"], "query": { "terms": { "_id": [ "' + id + '" ] } } }';
                    const get_es_url = options.kb_service_host + "/search/software-kb/_search";
                    getJsonFileWithData(get_es_url, local_es_query_json).then(responseJson => {
                        if (responseJson && responseJson['hits'] && responseJson['hits']['hits'] && responseJson['hits']['hits'].length == 1) {
                            const es_entity_fields = responseJson['hits']['hits'][0]['fields']

                            var localMentionData = '<a target="_blank" href="mentions.html?id=' + id + '&type=' + entity_type + '">';
                            localMentionData += es_entity_fields['number_mentions'] + ' mentions in ' + es_entity_fields['number_documents'] + ' documents';
                            localMentionData+= "</a>";

                            localMentionData += ' <span style="color:#999999;">(click to view mentions)</span>';

                            $("#mention-summary").empty();
                            $("#mention-summary").append(localMentionData);

                            // add timeline
                            if (es_entity_fields['timeline']) {
                                // key and value became array in the elasticsearch process, so we make them back to atomic value
                                for(var i in es_entity_fields['timeline']) {
                                    es_entity_fields['timeline'][i]["key"] = es_entity_fields['timeline'][i]["key"][0];
                                    es_entity_fields['timeline'][i]["doc_count"] = es_entity_fields['timeline'][i]["doc_count"][0];
                                }
                                // sort by key value ascending
                                es_entity_fields['timeline'].sort(function(a, b){return a.key-b.key});
                                timeline(es_entity_fields['timeline'], 300, "timeline");
                            }
                        }
                    });
                    $("#software-info").append(metadata);
                }

                if (record["claims"]) {
                    if ( (record["claims"]["P123"] && record["claims"]["P123"].length > 0) ||
                         (record["claims"]["P178"] && record["claims"]["P178"].length > 0) ) {
                        
                        // publisher or developer (in Wikidata)
                        metadata = '<div class="panel" id="publisher" style="margin-bottom:20!important; background-color:#ffffff; border: 1px;">';
                        metadata += '<div style="padding: 20px; width:100%;"><table>'+
                        '<tr><td><div style="width:60px;overflow: hidden;"><strong>Publisher</strong></div></td><td>&nbsp;&nbsp;</td> ';

                        metadata += '<td><div id="publisher-info"/></td><td>&nbsp;&nbsp;</td>';

                        metadata += '</tr></table></div>';
                        metadata += '</div>';

                        $("#software-info").append(metadata);
                        
                        getJsonFile(options.kb_service_host + "/entities/software/" + id+ "?format=codemeta").then(publicationsJson => {
                            if (publicationsJson && publicationsJson['record']) {
                                const best_publisher = publicationsJson['record']['publisher'];
                    
                                var support_count = -1;
                                var best_source = null;

                                // check full entry for provenance of the best publisher

                                // take WikiData publisher first, other curated source then, 
                                // and finally if nothing else most frequent extracted
                                if (record["claims"]["P178"] && record["claims"]["P178"].length > 0) {
                                    for(var i in record["claims"]["P178"]) {
                                        for(var j in record["claims"]["P178"][i]["references"]) {
                                            var localSource = record["claims"]["P178"][i]["references"][j]["P248"]["value"];       
                                            if (localSource === "Q2013") {
                                                best_source = "Wikidata";   
                                                break;
                                            }
                                        }
                                        if (best_source === "Wikidata") 
                                            break;
                                    }
                                }

                                if (best_source !== "Wikidata") {
                                    for(var i in record["claims"]["P123"]) {
                                        // check source
                                        for(var j in record["claims"]["P123"][i]["references"]) {
                                            var localSource = record["claims"]["P123"][i]["references"][j]["P248"]["value"];                            

                                            if (localSource === "Q2013") {
                                                best_source = "Wikidata";
                                                break;
                                            }
                                        }
                                        if (best_source === "Wikidata") 
                                            break;
                                    }
                                }

                                if (best_source !== "Wikidata") {
                                    for(var i in record["claims"]["P123"]) {
                                        if (record["claims"]["P123"][i]["value"] === best_publisher) {
                                            // check source
                                            for(var j in record["claims"]["P123"][i]["references"]) {
                                                var localSource = record["claims"]["P123"][i]["references"][j]["P248"]["value"];             
                                                var localCount = record["claims"]["P123"][i]["references"][j]["P248"]["count"]; 
                                                
                                                if (localCount > support_count) {
                                                    support_count = localCount;
                                                    best_source = localSource;
                                                }
                                            }
                                        }
                                    }
                                }

                                var best_source_msg = best_source;
                                if (support_count > 1) {
                                    best_source_msg += ', ' + support_count + ' occurences in mentions';
                                }

                                var publisherData = '<a target="_blank" href="' + 
                                options.kb_service_host + '/frontend/index.html?Entity=organizations&q=' + encodeURI(best_publisher) + '">' + 
                                encodedStr(best_publisher) + '</a> <span style="color:#999999;">(' + best_source_msg + ')</span>';

                                $("#publisher-info").append(publisherData);
                            }
                        });
                    }

                    
                    if (entity_type === 'software') {
                        metadata = '<div class="panel" id="citation1" style="margin-bottom:20!important; background-color:#ffffff; border: 1px;">';
                        metadata += '<div style="padding: 20px; width:100%;"><table style="width:100%;">'+
                            '<tr><td><div style="width:60px;overflow: hidden;"><strong>How is it cited?</strong></div></td>'+
                            '<td>&nbsp;&nbsp;</td><td><div id="best-reference"/></td></tr>';

                        // KB most frequent cited article together with the mentions

                        metadata += '</table></div>';
                        metadata += '</div>';

                        $("#software-info").append(metadata);

                        getJsonFile(options.kb_service_host + "/entities/software/" + id+ "/citeas?n_best=5").then(publicationsJson => {
                            var nothing = true;
                            if (publicationsJson && publicationsJson.records && publicationsJson.records.length > 0) {
                                for(var i in publicationsJson.records) {

                                    const count = publicationsJson.records[i]["size"];
                                    if (count && count >0) {
                                        getJsonFile(options.kb_service_host + "/entities/" + publicationsJson.records[i]["document"]).then(publicationJson => {
                                            const publication = publicationJson["record"];
                                            var localPublicationData = formatReference(publication);
                                            if (localPublicationData.length > 10) {
                                                localPublicationData += ' <span style="color:#999999;">(' + count + ' citations in mentions)</span>';
                                                localPublicationData += ' <a target="_blank" style="color:#999999;" href="' + 
                                                    options.kb_service_host + "/entities/" + publication["_id"] +'"><i class="fa fa-file"></i></a>';

                                                $("#best-reference").append("<p>" + localPublicationData + "</p>");
                                            }
                                        });
                                        nothing = false;
                                    }
                                }
                            } 
                            if (nothing) {
                                $("#best-reference").parent().parent().hide();
                            }
                        });
                    }
                
                    if (entity_type === 'software') {
                        metadata = '<div class="panel" id="citation2" style="margin-bottom:20!important; background-color:#ffffff; border: 1px;">';
                        metadata += '<div style="padding: 20px; width:100%;">'+
                            '<table style="width:100%;">'+
                            '<tr><td><div style="width:60px;overflow: hidden;"><strong>Citation requests</strong></div></td><td>&nbsp;&nbsp;</td>'+
                            '<td><div id="software-citation-request"/>'+
                            '<table><tr><td style="width:85px;"><a target="_blank" href="' + 
                                'http://citeas.org/cite/' + encodeURI(record["labels"]) + 
                                '/"><img src="data/images/citeas.png" alt="CiteAs" width="85px"/></a></td>'+
                                '<td><div id="citeas-reference"/></td></tr></table>' +
                            '</td></tr>';
                        
                        // KB curated reference, if any
                        //metadata += '<tr><td></td><td></td><td><div id="software-references"/></td><td>&nbsp;&nbsp;</td></tr>';
                        getJsonFile(options.kb_service_host + "/entities/software/" + id + "/references").then(publicationsJson => {
                            // list of documents used as reference in the software metadata, most of the time there is no
                            // such reference
                            if (publicationsJson && publicationsJson.records && publicationsJson.records.length > 0) {
                                for(var i in publicationsJson.records) {
                                    const count = publicationsJson.records[i]["size"];
                                    getJsonFile(options.kb_service_host + "/entities/" + publicationsJson.records[i]["document"]).then(publicationJson => {                                        
                                        const publication = publicationJson["record"];                                        
                                        var localReferenceData = formatReference(publication);
                                        localReferenceData += ' <span style="color:#999999;">(from software metadata)</span>';
                                        localReferenceData += ' <a target="_blank" style="color:#999999;" href="' + 
                                            options.kb_service_host + "/entities/" + publication["_id"] +'"><i class="fa fa-file"></i></a>';

                                    $("#software-citation-request").prepend("<p>" + localReferenceData + "</p>");
                                    });
                                }
                            } 
                        });

                        // direct software citation attempt, Force 11 style, e.g.
                        // Druskat, S., Spaaks, J. H., Chue Hong, N., Haines, R., Baker, J., Bliven, S., Willighagen, E., Pérez-Suárez, D., & Konovalov, A. (2021). 
                        // Citation File Format (Version 1.2.0) [Computer software]. https://doi.org/10.5281/zenodo.5171937
                        
                        //metadata += '<td style="padding-bottom: 10px; padding-top: 10px;"><div id="direct-software-citation"/></td><td>&nbsp;&nbsp;</td></tr>';

                        getJsonFile(options.kb_service_host + "/entities/software/" + id+ "?format=codemeta").then(publicationsJson => {
                            if (publicationsJson && publicationsJson['record']) {
                                var directCitation = '';
                                var start = true;
                                const publication = publicationsJson['record']
                                if (publication['author']) {
                                    for(var i in publication['author']) {
                                        if (!start) 
                                            directCitation += ', ';
                                        directCitation += publication['author'][i]['name'];
                                        start = false;
                                    }
                                } else if (publication['contributor']) {
                                    for(var i in publication['contributor']) {
                                        if (!start) 
                                            directCitation += ', ';
                                        directCitation += publication['contributor'][i]['name'];
                                        start = false;
                                    }
                                }

                                if (publication['date']) {
                                    if (!start) 
                                        directCitation += ' ';
                                    directCitation += '(' + publication['date'] + ').';
                                    start = false;
                                } else {
                                    if (!start) 
                                        directCitation += ".";
                                }

                                if (publication['name']) {
                                    if (!start) 
                                        directCitation += ' ';
                                    directCitation += publication['name'][0] + " [Computer software].";
                                    start = false;
                                }

                                if (publication['codeRepository']) {
                                    if (!start) 
                                        directCitation += ' ';
                                    directCitation += publication['codeRepository'];
                                    start = false;
                                } else if (publication['url']) {
                                    if (!start) 
                                        directCitation += ' ';
                                    directCitation += publication['url'];
                                    start = false;
                                }

                                $("#software-citation-request").prepend('<p>' + encodedStr(directCitation)+
                                    ' <span style="color:#999999;">(software citation)</span></p>');
                            }
                        });

                        // in any case, add a citeAs link
                        //var local_citeas_metadata = '';
                        //$("#software-citation-request").append("<p>" + local_citeas_metadata + "</p>");

                        getJsonFile("https://api.citeas.org/product/" + encodeURI(record["labels"]) + "?email=patrice.lopez@science-miner.com").then(publicationCiteAsJson => {
                            if (publicationCiteAsJson && publicationCiteAsJson["citations"] && publicationCiteAsJson["citations"].length>0) {
                                var localCiteAsData = publicationCiteAsJson["citations"][0]["citation"];

                                // explore the provenance tree, we keep only the provenance leaf (content non null without child)
                                var provenanceSources = [];
                                for(var j in publicationCiteAsJson["provenance"]) {
                                    if (publicationCiteAsJson["provenance"][j]["has_content"] == true && 
                                        publicationCiteAsJson["provenance"][j]["subject"] &&
                                        publicationCiteAsJson["provenance"][j]["subject"] !== "user input") {                                    
                                        if (provenanceSources.indexOf(publicationCiteAsJson["provenance"][j]["subject"]) == -1)
                                            provenanceSources.push(publicationCiteAsJson["provenance"][j]["subject"]);
                                    }
                                }
                                var provenanceInfo = '';
                                for(var i in provenanceSources) {
                                    if (provenanceInfo.length > 0) 
                                        provenanceInfo += ", ";
                                    provenanceInfo += provenanceSources[i];
                                }

                                if (provenanceInfo.length > 0) {
                                    localCiteAsData += ' <span style="color:#999999;">(' + provenanceInfo + ')</span>';
                                }
                                $("#citeas-reference").append(localCiteAsData);
                            }
                        });

                        metadata += '</table></div>';
                        metadata += '</div>';

                        $("#software-info").append(metadata);
                    }

                    if ((record["claims"]["P18"] && record["claims"]["P18"].length > 0) 
                            || (record["claims"]["P154"] && record["claims"]["P154"].length > 0)) {
                        // images
                        metadata = '<div class="panel" id="gallery" style="margin-bottom:20!important; background-color:#ffffff; border: 1px;">';
                        metadata += '<div style="padding: 20px; width:100%;"><table>'+
                            '<tr><td><div style="width:60px;overflow: hidden;"><strong>Gallery</strong></div></td><td>&nbsp;&nbsp;</td> ';

                        // TBD: check wikipedia image based on wikimedia english page id
                        //if (record["claims"]["P460"])
                        
                        if (record["claims"]["P154"] && record["claims"]["P154"].length > 0) {
                            for(var index in record["claims"]["P154"]) {
                                // logo
                                var imageUrl = "https://commons.wikimedia.org/w/index.php?title=Special:Redirect/file/" + 
                                    record["claims"]["P154"][index]["value"] + "&width=200";
                                metadata += '<td><img src="' + imageUrl + '" width="200"/></td><td>&nbsp;&nbsp;</td>';

                            }
                        }
                        if (record["claims"]["P18"] && record["claims"]["P18"].length > 0) {
                            for(var index in record["claims"]["P18"]) {
                                // images
                                var imageUrl = "https://commons.wikimedia.org/w/index.php?title=Special:Redirect/file/" + 
                                    record["claims"]["P18"][index]["value"] + "&width=200";
                                metadata += '<td><img src="' + imageUrl + '" width="200"/></td><td>&nbsp;&nbsp;</td>';

                            }
                        }
                        metadata += '</tr></table></div>';
                        metadata += '</div>';
                        $("#software-info").append(metadata);
                    }
                }
                
                metadata = "</div></div>"
                $("#software-info").append(metadata);
            });
        }

        var formatReference = function(publication) {
            var localPublicationData = '';
            var started = false;

            if (publication["metadata"]["title"] && publication["metadata"]["title"].length > 0) {
                localPublicationData += "<i>" + publication["metadata"]["title"][0] + "</i>";
                started = true;
            }

            if (publication["metadata"]["author"] && publication["metadata"]["author"].length > 0) {
                var firstAuthor = publication["metadata"]["author"][0];
                if (started) {
                    localPublicationData += ", ";
                }
                localPublicationData += publication["metadata"]["author"][0]["family"] + ' et al.';
                started = true;
            }

            if (publication["metadata"]["container-title"] && publication["metadata"]["container-title"].length > 0) {
                if (started) {
                    localPublicationData += ", ";
                }
                localPublicationData += publication["metadata"]["container-title"][0];
                started = true;
            }

            if (publication["metadata"]["issued"] && publication["metadata"]["issued"]["date-parts"] && 
                publication["metadata"]["issued"]["date-parts"].length > 0) {
                if (started) {
                    localPublicationData += ", ";
                }
                localPublicationData += publication["metadata"]["issued"]["date-parts"][0];
                started = true;
            } else if (publication["metadata"]["published-online"] && publication["metadata"]["published-online"]["date-parts"] && 
                publication["metadata"]["published-online"]["date-parts"].length > 0) {
                if (started) {
                    localPublicationData += ", ";
                }
                localPublicationData += publication["metadata"]["published-online"]["date-parts"][0];
                started = true;
            } else if (publication["metadata"]["date"]) {
                if (started) {
                    localPublicationData += ", ";
                }
                localPublicationData += publication["metadata"]["date"];
                started = true;
            }

            if (publication["metadata"]["publisher"]) {
                if (started) {
                    localPublicationData += ", ";
                }
                localPublicationData += publication["metadata"]["publisher"];
                started = true;
            }

            if (publication["metadata"]["DOI"]) {
                if (started) {
                    localPublicationData += ", ";
                }
                localPublicationData += 'DOI: <a target="_blank" href="https://doi.org/' +  
                    publication["metadata"]["DOI"] + '">' + publication["metadata"]["DOI"] + '</a>';
                started = true;
            }

            if (publication["metadata"]["pmid"]) {
                if (started) {
                    localPublicationData += ", ";
                }
                localPublicationData += 'PMID: ' + publication["metadata"]["pmid"];
                started = true;
            }

            if (publication["metadata"]["pmcid"]) {
                if (started) {
                    localPublicationData += ", ";
                }
                localPublicationData += 'PMC ID: <a target="_blank" href="https://www.ncbi.nlm.nih.gov/pmc/articles/' + 
                    publication["metadata"]["pmcid"] + '">' + publication["metadata"]["pmcid"] + '</a>';
                started = true;
            }

            return localPublicationData;
        }

        var fillDefaultColor = '#BC0E0E';
        //var fillDefaultColorLight = '#FE9A2E';
        var fillDefaultColorLight = '#fad7a0';

        var timeline = function(entries, width, place) {
            // entries is an array of pairs (key, doc_count)
            // where key is an integer representing elapsed days since 1970-01-01 UTC (compatibility to POSIX timestamp)
            // e.g. then date is obtained with var date = new Date(parseInt(key));

            // Add the last "blank" entry for proper timeline ending
            if (entries.length > 0) {
                //if (entries.length == 1) {    
                entries.push({doc_count: entries[entries.length - 1].doc_count});
            }
            // Set-up dimensions and scales for the chart
            var w = 250,
                h = 80,
                max = pv.max(entries, function (d) {
                    return d.doc_count;
                }),
                x = pv.Scale.linear(0, entries.length - 1).range(0, w),
                y = pv.Scale.linear(0, max).range(0, h);

            // Create the basis panel
            var vis = new pv.Panel()
                    .width(w+10)
                    .height(h+10)
                    .bottom(30)
                    .left(10)
                    .right(5)
                    .top(3);

            // no more than 10 textual elements (so years) on the X axis
            var rate = Math.floor(entries.length/8);
            var rank = -1;
            // Add the X-ticks
            vis.add(pv.Rule)
                    .data(entries)
                    .visible(function (d) {
                        return d.key;
                    })
                    .left(function () {
                        return x(this.index);
                    })
                    .bottom(-20)
                    .height(15)
                    .strokeStyle("#ccc")
                    // Add the tick label
                    .anchor("right")
                    .add(pv.Label)
                    .text(function (d) {
                        if ((rank != -1) && (rank != rate)) {
                            rank++;
                            return "";
                        }

                        rank = 0;
                        return d.key;
                    })
                    .textStyle("#333333")
                    .textMargin("2");

            var i = -1;
            // Add container panel for the chart
            vis.add(pv.Panel)
                    // Add the area segments for each entry
                    .add(pv.Area)
                    
                    // Pass the data to Protovis
                    .data(entries)
                    .bottom(0)
                    // Compute x-axis based on scale
                    .left(function (d) {
                        return x(this.index);
                    })
                    // Compute y-axis based on scale
                    .height(function (d) {
                        return y(d.doc_count);
                    })
                    // Make the chart curve smooth
                    .interpolate('cardinal')
                    // Divide the chart into "segments" (needed for interactivity)
                    .segmented(true)
                    .strokeStyle("#fff")
                    .fillStyle(fillDefaultColorLight)

                    // On "mouse down", perform action, such as filtering the results...
                    .event("mouseover", function (d) {
                        var year = entries[this.index].key;
                        var count = entries[this.index].doc_count;
                        $("#info-timeline").append('<strong>' + count + "</strong> mentions in <strong>" + year + "</strong>");
                    })

                    .event("mouseout", function (d) {
                        $("#info-timeline").empty();
                    })

                    // Add thick stroke to the chart
                    .anchor("top").add(pv.Line)
                        .lineWidth(3)
                        .strokeStyle(fillDefaultColor)

                    // Bind the chart to DOM element
                    .root.canvas(place)
                    // And render it.
                    .render();
        };

        // for getting wikipedia page image
        const wikimediaURL_prefix = 'https://';
        const wikimediaURL_suffix = '.wikipedia.org/w/api.php?action=query&prop=pageimages&format=json&pithumbsize=200&pageids=';

        supportedLanguages = ['en']
        wikimediaUrls = {};
        for (var i = 0; i < supportedLanguages.length; i++) {
            var lang = supportedLanguages[i];
            wikimediaUrls[lang] = wikimediaURL_prefix + lang + wikimediaURL_suffix
        }

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