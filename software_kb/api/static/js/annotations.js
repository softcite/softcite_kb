var displayTitleAnnotation = function (titleID) {

    //we load now in background the additional record information requiring a user interaction for
    // visualisation

    $('#titleNaked[rel="' + titleID + '"]').each(function () {
        if (options.collection == "npl") {
            // annotations for the title
            var index = $(this).attr('pos');
            var titleID = $(this).attr('rel');
            var localQuery = {"query": {"filtered": {"query": {"term": {"_id": titleID}}}}};
            $.ajax({
                type: "post",
                url: options.es_host+"/"+options.nerd_annotation_index+"/_search?",
                contentType: 'application/json',
                //dataType: 'jsonp',
                data: JSON.stringify(localQuery),
                success: function (data) {
                    displayAnnotations(data, index, titleID, 'title');
                }
            });
        }
    });
}

var displayAbstractAnnotation = function (abstractID) {
    $('#abstractNaked' + abstractID).each(function () {
        // annotations for the abstract
        var index = $(this).attr('pos');
        var titleID = $(this).attr('rel');
        var localQuery = {"query": {"filtered": {"query": {"term": {"_id": abstractID}}}}};

        $.ajax({
            type: "post",
            url: options.es_host+"/"+options.nerd_annotation_index+"/_search?",
            contentType: 'application/json',
            //dataType: 'jsonp',
            //data: {source: JSON.stringify(localQuery)},
            data: JSON.stringify(localQuery),
            success: function (data) {
                displayAnnotations(data, index, abstractID, 'abstract');
            }
        });
        // trigger MathJax on the abstract content
        MathJax.Hub.Queue(["Typeset",MathJax.Hub, 'abstractNaked'+abstractID]);
    });
}

var displayKeywordAnnotation = function (keywordIDs) {

    for (var p in keywordIDs) {
        $('#keywordsNaked[rel="' + keywordIDs[p] + '"]').each(function () {
            // annotations for the keywords
            var index = $(this).attr('pos');
            var keywordID = $(this).attr('rel');
            var localQuery = {"query": {"filtered": {"query": {"term": {"_id": keywordID}}}}};

            $.ajax({
                type: "post",
                url: options.es_host+"/"+options.nerd_annotation_index+"/_search?",
                contentType: 'application/json',
                //dataType: 'jsonp',
                data: JSON.stringify(localQuery),
                success: function (data) {
                    displayAnnotations(data, index, keywordID, 'keyword');
                }
            });
        });
    }

}

var displayAnnotations = function (data, index, id, origin) {
    var jsonObject = null;
    if (!data) {
        return;
    }
    if (data.hits) {
        if (data.hits.hits) {
            jsonObject = eval(data.hits.hits[0]);
        }
    }
    if (!jsonObject) {
        return;
    }

    // origin is title, abstract or keywords
    if (!options.data['' + origin]) {
        options.data['' + origin] = [];
    }
    if (origin == 'keyword') {
        if (!options.data['' + origin][index]) {
            options.data['' + origin][index] = [];
        }
        options.data['' + origin][index][id] = jsonObject['_source']['annotation']['nerd'];
    } else
        options.data['' + origin][index] = jsonObject['_source']['annotation']['nerd'];
    //console.log('annotation for ' + id);
    //console.log(jsonObject);

    //var text = jsonObject['_source']['annotation']['nerd']['text'];		
    var text = $('[rel="' + id + '"]').text();
    var entities = jsonObject['_source']['annotation']['nerd']['entities'];
    
    var lang = 'en'; //default
    var language = jsonObject['_source']['annotation']['nerd']['language'];
    if (language)
        lang = language.lang;

    var m = 0;
    var lastMaxIndex = text.length;
    //for(var m in entities) {
    for (var m = entities.length - 1; m >= 0; m--) {
        //var entity = entities[entities.length - m - 1];
        var entity = entities[m];
        entity['lang'] = lang;
        var chunk = entity.rawName;
        var domains = entity.domains;
        var domain = null;
        if (domains && domains.length > 0) {
            domain = domains[0].toLowerCase();
        }
        var label = null;
        if (entity.type)
            label = NERTypeMapping(entity.type, entity.chunk);
        else if (domain)
            label = domain;
        else
            label = chunk;
        var start = parseInt(entity.offsetStart, 10);
        var end = parseInt(entity.offsetEnd, 10);

        // keeping track of the lastMaxIndex allows to handle nbest results, e.g. possible
        // overlapping annotations to display as infobox, but with only one annotation
        // tagging the text
        if (start > lastMaxIndex) {
            // we have a problem in the initial sort of the entities
            // the server response is not compatible with the client 
            console.log("Sorting of entities as present in the server's response not valid for this client.");
        } else if ((start == lastMaxIndex) || (end > lastMaxIndex)) {
            // overlap
            end = lastMaxIndex;
        } else {
            // we produce the annotation on the string
            if (origin == "abstract") {
                text = text.substring(0, start) +
                        '<span id="annot-abs-' + index + '-' + (entities.length - m - 1) +
                        '" data-color="' + label + '">' +
                        '<span class="label ' + label +
                        '" style="cursor:hand;cursor:pointer;white-space: normal;" >'
                        + text.substring(start, end) + '</span></span>'
                        + text.substring(end, text.length + 1);
            } else if (origin == "keyword") {
                text = text.substring(0, start) +
                        '<span id="annot-key-' + index + '-' + (entities.length - m - 1) + '-' + id
                        + '" data-color="' + label + '">' +
                        '<span class="label ' + label + '" style="cursor:hand;cursor:pointer;" >'
                        + text.substring(start, end) + '</span></span>'
                        + text.substring(end, text.length + 1);
            } else {
                text = text.substring(0, start) +
                        '<span id="annot-' + index + '-' + (entities.length - m - 1) +
                        '" data-color="' + label + '">' +
                        '<span class="label ' + label + '" style="cursor:hand;cursor:pointer;" >'
                        + text.substring(start, end) + '</span></span>'
                        + text.substring(end, text.length + 1);
            }
            lastMaxIndex = start;
        }
    }

    //var result = '<strong><span style="font-size:13px">' + text + '<span></strong>';
    $('[rel="' + id + '"]').html(text);

    // now set the popovers/view event 
    var m = 0;
    for (var m in entities) {
        // set the info box
        if (origin == "abstract") {
            $('#annot-abs-' + index + '-' + m).hover(viewEntity);

//            $('#annot-abs-' + index + '-' + m).popover({
//                html: true,
//                placement: $.fn.placement,
//                //trigger:'hover',
//                content: function () {
//                    return $('#detailed_annot-' + index).html();
//                }});
        } else if (origin == "keyword") {
            $('#annot-key-' + index + '-' + m + '-' + id).hover(viewEntity);
        } else {
            $('#annot-' + index + '-' + m).click(function () {
                if (!$("#abstract_keywords_" + index).is(":visible"))
                    $('#button_abstract_keywords_collapse_' + index).click();
                if ($("#abstract_keywords_" + index).is(":visible"))
                    $('#button_abstract_keywords_collapse_' + index).click();
            });
            $('#annot-' + index + '-' + m).hover(viewEntity);
        }
    }
}



/** 
 * View the full entity information in the infobox 
 */
function viewEntity(event) {

    event.preventDefault();
    // currently entity can appear in the title, abstract or keywords
    // the origin is visible in the event origin id, as well as the "coordinates" of the entity 

    var localID = $(this).attr('id');

//console.log(localID);

    var resultIndex = -1;
    var abstractSentenceNumber = -1;
    var entityNumber = -1;
    var idNumber = null;

    var inAbstract = false;
    var inKeyword = false;
    if (localID.indexOf("-abs-") != -1) {
        // the entity is located in the abstract
        inAbstract = true;
        var ind1 = localID.indexOf('-');
        ind1 = localID.indexOf('-', ind1 + 1);
        //var ind2 = localID.indexOf('-', ind1+1);
        var ind3 = localID.lastIndexOf('-');
        resultIndex = parseInt(localID.substring(ind1 + 1, ind3));
        //abstractSentenceNumber = parseInt(localID.substring(ind2+1,ind3));
        entityNumber = parseInt(localID.substring(ind3 + 1, localID.length));
    } else if (localID.indexOf("-key-") != -1) {
        // the entity is located in the keywords
        inKeyword = true;
        var ind1 = localID.indexOf('-');
        ind1 = localID.indexOf('-', ind1 + 1);
        var ind2 = localID.indexOf('-', ind1 + 1);
        var ind3 = localID.lastIndexOf('-');
        resultIndex = parseInt(localID.substring(ind1 + 1, ind3));
        entityNumber = parseInt(localID.substring(ind2 + 1, ind3));
        idNumber = localID.substring(ind3 + 1, localID.length);
    } else {
        // the entity is located in the title
        var ind1 = localID.indexOf('-');
        var ind2 = localID.lastIndexOf('-');
        resultIndex = parseInt(localID.substring(ind1 + 1, ind2));
        entityNumber = parseInt(localID.substring(ind2 + 1, localID.length));

        // and, if not expended, we need to expend the record collapsable to show the info box
        //('#myCollapsible_'+resultIndex).collapse('show');
    }

    var entity = null;
    var localSize = -1;

    if (inAbstract) {
        //console.log(resultIndex + " " + entityNumber);
        //console.log(options.data['abstract'][resultIndex]['entities']);

        if ((options.data['abstract'][resultIndex])
                && (options.data['abstract'][resultIndex])
                && (options.data['abstract'][resultIndex]['entities'])
                ) {
            localSize = options.data['abstract'][resultIndex]
            ['entities'].length;
            entity = options.data['abstract'][resultIndex]
            ['entities'][localSize - entityNumber - 1];
        }
    } else if (inKeyword) {
        //console.log(resultIndex + " " + entityNumber + " " + idNumber);
        //console.log(options.data['keyword'][resultIndex][idNumber]['entities']);

        if ((options.data['keyword'][resultIndex])
                && (options.data['keyword'][resultIndex][idNumber])
                && (options.data['keyword'][resultIndex][idNumber]['entities'])
                ) {
            localSize = options.data['keyword'][resultIndex][idNumber]
            ['entities'].length;
            entity = options.data['keyword'][resultIndex][idNumber]
            ['entities'][localSize - entityNumber - 1];
        }
    } else {
        //console.log(resultIndex + " " + " " + entityNumber);
        //console.log(options.data['title'][resultIndex]['entities']);

        if ((options.data['title'])
                && (options.data['title'][resultIndex])
                && (options.data['title'][resultIndex]['entities'])
                ) {
            localSize = options.data['title'][resultIndex]['entities'].length;
            entity = options.data['title'][resultIndex]['entities'][localSize - entityNumber - 1];
        }
    }

    var string = "";
    if (entity != null) {
        var lang = 'en'; //default
        lang = entity['lang'];

        //console.log(entity);
        var domains = entity.domains;
        if (domains && domains.length > 0) {
            domain = domains[0].toLowerCase();
        }
        var type = entity.type;

        var colorLabel = null;
        if (type)
            colorLabel = type;
        else if (domains && domains.length > 0) {
            colorLabel = domain;
        } else
            colorLabel = entity.rawName;

        var start = parseInt(entity.offsetStart, 10);
        var end = parseInt(entity.offsetEnd, 10);

        var subType = entity.subtype;
        var conf = entity.nerd_score;
        if (conf && conf.length > 4)
            conf = conf.substring(0, 4);
        var definitions = entity.definitions;
        var wikipedia = entity.wikipediaExternalRef;
        var content = entity.rawName; //$(this).text();
        var preferredTerm = entity.preferredTerm;

        var sense = null;
        if (entity.sense)
            sense = entity.sense.fineSense;

        string += "<div class='info-sense-box " + colorLabel +
                "' ><h3 style='color:#FFF;padding-left:10px; font-weight:bold; font-size:16;'>" + content.toUpperCase() +
                "</h3>";
        string += "<div class='container-fluid' style='background-color:#F9F9F9;color:#70695C;border:padding:5px;'>" +
                "<table style='width:100%;background-color:#fff;border:0px;'><tr style='background-color:#fff;border:0px;'><td style='background-color:#fff;border:0px;'>";

        if (preferredTerm) {
            string += "<p>Normalized: <b>" + preferredTerm + "</b></p>";
        }

        if (type)
            string += "<p>Type: <b>" + type + "</b></p>";

        if (sense)
            string += "<p>Sense: <b>" + sense + "</b></p>";

        if (domains && domains.length > 0) {
            string += "<p>Domains: <b>";
            for (var i = 0; i < domains.length; i++) {
                if (i != 0)
                    string += ", ";
                string += domains[i].replace("_", " ");
            }
            string += "</b></p>";
        }

        string += "<p>conf: <i>" + conf + "</i></p>";

        string += "</td><td style='align:right;background-color:#fff' width='50%''>";

        if (wikipedia != null) {
            //var file = wikipediaHTMLResult(wikipedia, resultIndex);
//            urlImage += '?maxwidth=150';
//            urlImage += '&maxheight=150';
//            urlImage += '&key=' + options.api_key;
            string += 
            '<span style="align:right;" id="img-' + wikipedia + '-'+resultIndex+'"><script type="text/javascript">lookupWikiMediaImage("'+
                wikipedia+'", "'+lang+'", "img-'+wikipedia+'-'+resultIndex+'")</script></span>';
        }

        string += "</td></tr></table>";

        if ((definitions != null) && (definitions.length > 0)) {
            var localHtml = wiki2html(definitions[0]['definition'], lang);
            //string += "<p style='align:justify;text-align:justify; text-justify:inter-word; width:100%;'>" + localHtml + "</p>";
            string += "<p><div class='wiky_preview_area2' style='align:justify;text-align:justify; text-justify:inter-word; width:100%;'>"+localHtml+"</div></p>";
        }

        if (wikipedia != null) {
            string += '<p>Reference: '
            //string += '<a href="http://en.wikipedia.org/wiki?curid=' +
            //        wikipedia +
            //        '" target="_blank"><img style="max-width:28px;max-height:22px;margin-top:5px;" src="data/images/wikipedia.png"/></a>';

            string += '<a href="http://en.wikipedia.org/wiki?curid=' +
                            wikipedia +
                    '" target="_blank"><img style="max-width:28px;max-height:22px;" src="data/images/wikipedia.png"/></a>';        
        }
        string += '</p>';


        string += "</div></div>";
        $('#detailed_annot-' + resultIndex).html(string);
        $('#detailed_annot-' + resultIndex).show();
    }
}



window.lookupWikiMediaImage = function (wikipedia, lang, id) {
    // first look in the local cache
    if (lang + wikipedia in options.imgCache) {
        var imgUrl = options.imgCache[lang + wikipedia];
        var document = (window.content) ? window.content.document : window.document;
        var spanNode = document.getElementById(id);
        if (spanNode != null)
            spanNode.innerHTML = '<img style="float:right;" src="' + imgUrl + '"/>';
    } else {
        // otherwise call the wikipedia API
        var theUrl = null;
        if (lang == 'fr')
            theUrl = options.wikimediaURL_FR + wikipedia;
        else if (lang == 'de')
            theUrl = options.wikimediaURL_DE + wikipedia;
        else
            theUrl = options.wikimediaURL_EN + wikipedia;
        // note: we could maybe use the en crosslingual correspondance for getting more images in case of non-English pages
        $.ajax({
            url: theUrl,
            jsonp: "callback",
            dataType: "jsonp",
            xhrFields: {withCredentials: true},
            success: function (response) {
                var document = (window.content) ? window.content.document : window.document;
                //var spanNode = document.getElementById("img-" + wikipedia);
                var spanNode = document.getElementById(id);
                if (response.query && spanNode) {
                    if (response.query.pages[wikipedia]) {
                        if (response.query.pages[wikipedia].thumbnail) {
                            var imgUrl = response.query.pages[wikipedia].thumbnail.source;
                            if (spanNode != null)
                                spanNode.innerHTML = '<img style="float:right;" src="' + imgUrl + '"/>';
                            // add to local cache for next time
                            options.imgCache[lang + wikipedia] = imgUrl;
                        }
                    }
                }
            }
        });
    }
}

var parseDisambNERD = function (sdata) {
    var jsonObject = JSON.parse(sdata);
    return jsonObject;
};

var getPieceShowexpandNERD = function (jsonObject) {
    var lang = 'en'; //default
    var language = jsonObject.language;
    if (language)
        lang = language.lang;
    var piece = '<div class="well col-md-11" style="background-color:#F7EDDC;">';
    if (jsonObject['entities']) {
        piece += '<table class="table" style="border:1px solid white;">';
        for (var sens in jsonObject['entities']) {
            var entity = jsonObject['entities'][sens];
            var domains = entity.domains;
            if (domains && domains.length > 0) {
                domain = domains[0].toLowerCase();
            }
            var type = entity.type;

            var colorLabel = null;
            if (type)
                colorLabel = type;
            else if (domains && domains.length > 0) {
                colorLabel = domain;
            } else
                colorLabel = entity.rawName;

            var start = parseInt(entity.offsetStart, 10);
            var end = parseInt(entity.offsetEnd, 10);

            var subType = entity.subtype;
            var conf = entity.nerd_score;
            if (conf && conf.length > 4)
                conf = conf.substring(0, 4);
            var definitions = entity.definitions;
            var wikipedia = entity.wikipediaExternalRef;
            var content = entity.rawName; //$(this).text();
            var preferredTerm = entity.preferredTerm;

            piece += '<tr id="selectLine' + sens + '" href="'
                    + wikipedia + '" rel="$teiCorpus.$standoff.$nerd.wikipediaExternalRef"><td id="selectArea' + sens + '" href="'
                    + wikipedia + '" rel="$teiCorpus.$standoff.$nerd.wikipediaExternalRef">';
            piece += '<div class="checkbox checkbox-inline checkbox-danger" id="selectEntityBlock' +
                    sens + '" href="' + wikipedia + '" rel="$teiCorpus.$standoff.$nerd.wikipediaExternalRef">';
            piece += '<input type="checkbox" id="selectEntity' + sens
                    + '" name="selectEntity' + sens + '" value="0" href="'
                    + preferredTerm + '" rel="$teiCorpus.$standoff.$nerd.preferredTerm" display="concepts">';
            piece += '<label for="selectEntity' + sens + '" id="label' + sens + '"> <strong>' + entity.rawName + '&nbsp;</strong> </label></div></td>';
            
            //if (conf)
            //     piece += '<p><b>Conf</b>: ' + conf + '</p>';

            var localHtml = "";
            if (definitions && definitions.length > 0)
                localHtml = wiki2html(definitions[0]['definition'], lang);

            /*if ( preferredTerm && (entity.rawName.toLowerCase() != preferredTerm.toLowerCase()) ) {   
                piece += '<td><b>' + preferredTerm + ': </b>' +
                        localHtml
                        + '</td><td>';
            } else */{
                piece += '<td>' +
                        localHtml
                        + '</td><td>';
            }

            piece += '<td width="25%">';
            piece += 
            '<span id="img-disamb-' + wikipedia + '-' + sens+'"><script type="text/javascript">lookupWikiMediaImage("'+
                wikipedia+'", "'+lang+'", "img-disamb-' + wikipedia + '-' + sens+'")</script></span>';
            piece += '</td><td>';
            piece += '<table><tr><td>';

            if (wikipedia) {
                piece += '<a href="http://en.wikipedia.org/wiki?curid=' +
                        wikipedia +
                        '" target="_blank"><img style="max-width:28px;max-height:22px;" src="data/images/wikipedia.png"/></a>';
            }
            piece += '</td></tr><tr><td>';

            piece += '</td></tr></table>';

            piece += '</td></tr>';
        }
        piece += '</table>';
    }

    piece += '</div>';
    piece += '<div class="col-md-1"><a id="close-disambiguate-panel" onclick=\'$("#disambiguation_panel").hide()\'>'+
        '<span class="glyphicon glyphicon-remove" style="color:black;"></span></a></div>';

    return piece;
};

var activateDisambButton = function (num) {
    $('#disambiguate' + num).attr("disabled", false);
};

var checkDisambButton = function () {
    var num = $(this).attr("id").match(/\d+/)[0]
    if ($('#facetview_freetext'+num).val()) {
        $('#disambiguate' + num).attr("disabled", false);
    }
    else {
        $('#disambiguate' + num).attr("disabled", true);
    }
};

var deactivateDisambButton = function (num) {
    $('#disambiguate' + num).attr("disabled", true);
};
