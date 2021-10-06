// do search options
var fixmatch = function (event) {
    event.preventDefault();
    if ($(this).attr('id') == "facetview_partial_match") {
        var newvals = $('#facetview_freetext').val().replace(/"/gi, '').replace(/\*/gi, '').replace(/\~/gi, '').split(' ');
        var newstring = "";
        for (item in newvals) {
            if (newvals[item].length > 0 && newvals[item] != ' ') {
                if (newvals[item] == 'OR' || newvals[item] == 'AND') {
                    newstring += newvals[item] + ' ';
                } else {
                    newstring += '*' + newvals[item] + '* ';
                }
            }
        }
        $('#facetview_freetext').val(newstring);
    }
    else if ($(this).attr('id') == "facetview_fuzzy_match") {
        var newvals = $('#facetview_freetext').val().replace(/"/gi, '').replace(/\*/gi, '').replace(/\~/gi, '').split(' ');
        var newstring = "";
        for (item in newvals) {
            if (newvals[item].length > 0 && newvals[item] != ' ') {
                if (newvals[item] == 'OR' || newvals[item] == 'AND') {
                    newstring += newvals[item] + ' ';
                } else {
                    newstring += newvals[item] + '~ ';
                }
            }
        }
        $('#facetview_freetext').val(newstring);
    }
    else if ($(this).attr('id') == "facetview_exact_match") {
        var newvals = $('#facetview_freetext').val().replace(/"/gi, '').replace(/\*/gi, '').replace(/\~/gi, '').split(' ');
        var newstring = "";
        for (item in newvals) {
            if (newvals[item].length > 0 && newvals[item] != ' ') {
                if (newvals[item] == 'OR' || newvals[item] == 'AND') {
                    newstring += newvals[item] + ' ';
                } else {
                    newstring += '"' + newvals[item] + '" ';
                }
            }
        }
        $.trim(newstring, ' ');
        $('#facetview_freetext').val(newstring);
    }
    else if ($(this).attr('id') == "facetview_match_all") {
        $('#facetview_freetext').val($.trim($('#facetview_freetext').val().replace(/ OR /gi, ' ')));
        $('#facetview_freetext').val($('#facetview_freetext').val().replace(/ /gi, ' AND '));
    }
    else if ($(this).attr('id') == "facetview_match_any") {
        $('#facetview_freetext').val($.trim($('#facetview_freetext').val().replace(/ AND /gi, ' ')));
        $('#facetview_freetext').val($('#facetview_freetext').val().replace(/ /gi, ' OR '));
    }
    $('#facetview_freetext').focus().trigger('keyup');
};

// this is the list of Lucene characters to escape when not used as lucene operators:  +-&amp;|!(){}[]^"~*?:\
var lucene_specials =
        ["-", "[", "]", "{", "}", "(", ")", "*", "+", "?", "\\", "^", "|", "&", "!", '"', "~", ":"];

function addCommas(nStr) {
    nStr += '';
    x = nStr.split('.');
    x1 = x[0];
    x2 = x.length > 1 ? '.' + x[1] : '';
    var rgx = /(\d+)(\d{3})/;
    while (rgx.test(x1)) {
        x1 = x1.replace(rgx, '$1' + ',' + '$2');
    }
    return x1 + x2;
}

var Base64 = {
    // private property
    _keyStr: "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/=",
    // public method for encoding
    encode: function (input) {
        var output = "";
        var chr1, chr2, chr3, enc1, enc2, enc3, enc4;
        var i = 0;

        input = Base64._utf8_encode(input);

        while (i < input.length) {

            chr1 = input.charCodeAt(i++);
            chr2 = input.charCodeAt(i++);
            chr3 = input.charCodeAt(i++);

            enc1 = chr1 >> 2;
            enc2 = ((chr1 & 3) << 4) | (chr2 >> 4);
            enc3 = ((chr2 & 15) << 2) | (chr3 >> 6);
            enc4 = chr3 & 63;

            if (isNaN(chr2)) {
                enc3 = enc4 = 64;
            } else if (isNaN(chr3)) {
                enc4 = 64;
            }

            output = output +
                    this._keyStr.charAt(enc1) + this._keyStr.charAt(enc2) +
                    this._keyStr.charAt(enc3) + this._keyStr.charAt(enc4);
        }

        return output;
    },
    // public method for decoding
    decode: function (input) {
        var output = "";
        var chr1, chr2, chr3;
        var enc1, enc2, enc3, enc4;
        var i = 0;

        input = input.replace(/[^A-Za-z0-9\+\/\=]/g, "");

        while (i < input.length) {

            enc1 = this._keyStr.indexOf(input.charAt(i++));
            enc2 = this._keyStr.indexOf(input.charAt(i++));
            enc3 = this._keyStr.indexOf(input.charAt(i++));
            enc4 = this._keyStr.indexOf(input.charAt(i++));

            chr1 = (enc1 << 2) | (enc2 >> 4);
            chr2 = ((enc2 & 15) << 4) | (enc3 >> 2);
            chr3 = ((enc3 & 3) << 6) | enc4;

            output = output + String.fromCharCode(chr1);

            if (enc3 != 64) {
                output = output + String.fromCharCode(chr2);
            }
            if (enc4 != 64) {
                output = output + String.fromCharCode(chr3);
            }

        }

        output = Base64._utf8_decode(output);

        return output;

    },
    // private method for UTF-8 encoding
    _utf8_encode: function (string) {
        string = string.replace(/\r\n/g, "\n");
        var utftext = "";

        for (var n = 0; n < string.length; n++) {

            var c = string.charCodeAt(n);

            if (c < 128) {
                utftext += String.fromCharCode(c);
            }
            else if ((c > 127) && (c < 2048)) {
                utftext += String.fromCharCode((c >> 6) | 192);
                utftext += String.fromCharCode((c & 63) | 128);
            }
            else {
                utftext += String.fromCharCode((c >> 12) | 224);
                utftext += String.fromCharCode(((c >> 6) & 63) | 128);
                utftext += String.fromCharCode((c & 63) | 128);
            }

        }

        return utftext;
    },
    // private method for UTF-8 decoding
    _utf8_decode: function (utftext) {
        var string = "";
        var i = 0;
        var c = c1 = c2 = 0;

        while (i < utftext.length) {

            c = utftext.charCodeAt(i);

            if (c < 128) {
                string += String.fromCharCode(c);
                i++;
            }
            else if ((c > 191) && (c < 224)) {
                c2 = utftext.charCodeAt(i + 1);
                string += String.fromCharCode(((c & 31) << 6) | (c2 & 63));
                i += 2;
            }
            else {
                c2 = utftext.charCodeAt(i + 1);
                c3 = utftext.charCodeAt(i + 2);
                string += String.fromCharCode(((c & 15) << 12) | ((c2 & 63) << 6) | (c3 & 63));
                i += 3;
            }

        }

        return string;
    }

};

UTF8 = {
    encode: function (s) {
        for (var c, i = -1, l = (s = s.split("")).length, o = String.fromCharCode; ++i < l;
                s[i] = (c = s[i].charCodeAt(0)) >= 127 ? o(0xc0 | (c >>> 6)) + o(0x80 | (c & 0x3f)) : s[i]
                )
            ;
        return s.join("");
    },
    decode: function (s) {
        for (var a, b, i = -1, l = (s = s.split("")).length, o = String.fromCharCode, c = "charCodeAt"; ++i < l;
                ((a = s[i][c](0)) & 0x80) &&
                (s[i] = (a & 0xfc) == 0xc0 && ((b = s[i + 1][c](0)) & 0xc0) == 0x80 ?
                        o(((a & 0x03) << 6) + (b & 0x3f)) : o(128), s[++i] = "")
                )
            ;
        return s.join("");
    }
};

function NERTypeMapping(type, def) {
    var label = null;
    switch (type) {
        case "location/N1":
            label = "location";
            break;
        case "event/N1":
            label = "event";
            break;
        case "time_period/N1":
            label = "period";
            break;
        case "person/N1":
            label = "person";
            break;
        case "national/J3":
            label = "national";
            break;
        case "acronym/N1":
            label = "acronym";
            break;
        case "institution/N2":
            label = "institution";
            break;
        case "measure/N3":
            label = "measure";
            break;
        case "organizational_unit/N1":
            label = "organization";
            break;
        case "title/N6":
            label = "title";
            break;
        case "artifact/N1":
            label = "artifact";
            break;
        default:
            label = def;
    }
    return label;
}

/**
 *  This is a primitive function that return the json object corresponding to a 
 *  loosy elasticsearch json path in the array type of structures return by elasticsearch
 *  fields query parameter.
 * 
 *  In case of multiple sub array (corresponding to several distinct results following
 *  the same elasticsearch json path), we aggregate the final field values in the result.  
 * 
 *  The result is an array. 
 */
var accessJsonPath = function (jsonArray, path) {
    var res = [];
    if (!path) {
        return res;
    }

    var subPath = null;
    var indd = path.indexOf('.');
    if (indd != -1) {
        subPath = path.substring(indd + 1, path.length);
    }

    if (!subPath) {
        for (var subObj in jsonArray) {
            res.push(jsonArray[subObj]);
        }
    }
    else {
        for (var subObj in jsonArray) {
            var localRes = accessJsonPath(jsonArray[subObj], subPath)
            for (var ress in localRes) {
                res.push(localRes[ress]);
            }
        }
    }

    return res;
};





var computeIdString = function (acceptType, date, host, path, queryParameters) {
    return appendStrings(acceptType, date, host, path, computeSortedQueryString(queryParameters));
};

var computeSortedQueryString = function (queryParameters) {
    // parameters are stored in a json object
    // we sort
    queryParameters = queryParameters.sort(function (a, b) {
        for (var key1 in a) {
            for (var key2 in b) {
                if (key1 < key2)
                    return -1;
                else if (key1 > key2)
                    return 1;
                else {
                    return a[key1] < b[key2] ? -1 : 1;
                }
            }
        }
    });
    var parameterStrings = "";
    var first = true;
    for (var param in queryParameters) {
        var obj = queryParameters[param];
        for (var key in obj) {
            if (first) {
                parameterStrings += key + "=" + decodeURIComponent(queryParameters[param][key]);
                first = false;
            }
            else {
                parameterStrings += "&" + key + "=" + decodeURIComponent(queryParameters[param][key]);
            }
        }
    }
    return parameterStrings;
};


// compute the digest base on idString and the key via HmacSHA1 hash
var buildDigest = function (key, idString) {
    // idString should be encoded in utf-8
    idString = UTF8.encode(idString);
    var signature = CryptoJS.HmacSHA1(idString, key);
    var encodedData = signature.toString(CryptoJS.enc.Base64);

    return encodedData;
};

// append the strings together with '\n' as a delimiter
var appendStrings = function (acceptType, date, host, path, queryParameters) {
    var stringBuilder = acceptType + "\n";
    stringBuilder += date + "\n";
    stringBuilder += host + "\n";
    stringBuilder += path + "\n";
    stringBuilder += queryParameters + "\n";
    return stringBuilder;
};


var parseDisamb = function (sdata) {
    var resObj = {};
    resObj['paraphrases'] = [];

    var ind1 = sdata.indexOf("Content-Type: application/json");
    var ind10 = sdata.indexOf("{", ind1);
    var ind11 = sdata.indexOf("\n", ind10);

    var ind2 = sdata.indexOf("Content-Type: application/x-semdoc+xml");

    var jsonStr = sdata.substring(ind10, ind11);
    var jsonObject = JSON.parse(jsonStr);

    //console.log(jsonObject);

    for (var surf in jsonObject['paraphrases']) {
        resObj['paraphrases'].push(jsonObject['paraphrases'][surf]['surface']);
    }

    // we now parse the xml part
    var ind22 = sdata.indexOf("-------", ind2);
    var ind21 = sdata.indexOf("\n", ind2);
    var xmlStr = sdata.substring(ind21, ind22).trim();
    //console.log(xmlStr);

    resObj['senses'] = [];
    //for (var sens in $(xmlStr).find("sense")) {
    $('sense', xmlStr).each(function (i) {
        sens = $(this);
        //console.log(sens);
        var label = $(sens).attr("fsk");
        if (label) {
            var ind = label.indexOf("/");
            if (ind != -1) {
                label = label.substring(0, ind)
            }
            label = label.replace('_', ' ');
        }
        var desc = $(sens).find("desc").text();
        var ref = $(sens).find("extRef");
        var wiki = null;
        var scope = true;
        if (ref) {
            if (ref.text().indexOf("wikipedia") != -1) {
                if ($(ref).find("ref")) {
                    wiki = $(ref).find("ref").text();
                }
            }
            if ((ref.text().indexOf("mb_") != -1) ||
                    (sens.text().indexOf("musical_composition/N1") != -1)) {
                scope = false;
            }
        }
        if (scope) {
            if (wiki) {
                resObj['senses'].push({'label': label, 'desc': desc, 'wiki': wiki});
            }
            else {
                resObj['senses'].push({'label': label, 'desc': desc});
            }
        }
    });

    return resObj;
};

        