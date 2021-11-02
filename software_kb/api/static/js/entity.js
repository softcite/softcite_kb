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

        var showEntityMetadata = function(id) {
            // get json object for software
            getJsonFile(options.kb_service_host + "/entities/"+entity_type+"/"+id).then(softwareJson => {
                record = softwareJson["record"];

                metadata = '<div class="panel" style="margin-bottom:20!important; background-color:#ffffff; border: 1px;">';
                metadata += '<div style="padding: 20px;">'
                metadata += '<p><strong>' + record["labels"] + "</strong>";
                if (record["descriptions"]) {
                    metadata += " - " + record["descriptions"] 
                }

                metadata += ' <a target="_blank" style="color:#999999;" href="' + 
                            options.kb_service_host + "/entities/"+entity_type+"/" + id +'"><i class="fa fa-file"></i></a>'

                metadata += "</p>"
                if (record["summary"]) {
                    var localHtml = wiki2html(record["summary"], "en");
                    metadata += localHtml;
                }
                
                metadata += "</div></div>"
                $("#software-info").append(metadata);
            });
        }

        showEntityMetadata(entity_id);
    }

})(jQuery);