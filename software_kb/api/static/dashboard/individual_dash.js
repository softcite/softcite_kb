
function InitPublicationsByYear() {
    $("#chart-01-title").text("Publications over time");
    $.ajax({
        type: "get",
        url: api_urls.publications + "/_search",
        data: {source: PublicationsByYearESQuery()},
        //processData: true, 
        //dataType: "jsonp",
        success: function (data) {
            var margin = {top: 10, right: 10, bottom: 50, left: 30},
                    width = 370 - margin.left - margin.right,
                    height = 250 - margin.top - margin.bottom;
            var touchdowns = data.aggregations.publication_date.buckets;
            var x = [];
            var y = [];

            touchdowns.forEach(function (datum, i) {

                x.push(datum["key_as_string"].split("-")[0]);
                y.push(datum["doc_count"]);
            });

            var dataSet = [{
                    mode: 'lines',
                    x: x,
                    y: y
                }]

            var layout = {
                //title: 'Time series with range slider and selectors',
                xaxis: {
                    rangeslider: {}
                },
                yaxis: {
                    title: "Number of documents",
                    fixedrange: true
                }
            };

            Plotly.plot('chart-01', dataSet, layout);
        }
    });
}

function InitWikipediaCategories() {
    $("#chart-06-title").text("Wikipedia categories");
    $.ajax({
        type: "get",
        url: api_urls.publications + "/_search",
        data: {source: WikipediaCategoriesESQuery()},
        success: function (data) {
            var touchdowns = data.aggregations.category.buckets;

            var labels = [];
            var values = [];

            touchdowns.forEach(function (datum, i) {

                labels.push(datum["key"]);
                values.push(datum["doc_count"]);
            });
            var data = [{
                    values: values,
                    labels: labels,
                    type: 'pie',
                    textinfo: 'none',
                    font: {
                        color: 'rgb(0, 0, 0)',
                        size: 8
                    }
                }];

            var layout = {
                showlegend: false,
                height: 500,
                width: 400
            };

            Plotly.newPlot('chart-06', data, layout);
        }
    });
}

var iso3 = {"BD": "BGD", "BE": "BEL", "BF": "BFA", "BG": "BGR", "BA": "BIH", "BB": "BRB", "WF": "WLF", "BL": "BLM", "BM": "BMU", "BN": "BRN", "BO": "BOL", "BH": "BHR", "BI": "BDI", "BJ": "BEN", "BT": "BTN", "JM": "JAM", "BV": "BVT", "BW": "BWA", "WS": "WSM", "BQ": "BES", "BR": "BRA", "BS": "BHS", "JE": "JEY", "BY": "BLR", "BZ": "BLZ", "RU": "RUS", "RW": "RWA", "RS": "SRB", "TL": "TLS", "RE": "REU", "TM": "TKM", "TJ": "TJK", "RO": "ROU", "TK": "TKL", "GW": "GNB", "GU": "GUM", "GT": "GTM", "GS": "SGS", "GR": "GRC", "GQ": "GNQ", "GP": "GLP", "JP": "JPN", "GY": "GUY", "GG": "GGY", "GF": "GUF", "GE": "GEO", "GD": "GRD", "GB": "GBR", "GA": "GAB", "SV": "SLV", "GN": "GIN", "GM": "GMB", "GL": "GRL", "GI": "GIB", "GH": "GHA", "OM": "OMN", "TN": "TUN", "JO": "JOR", "HR": "HRV", "HT": "HTI", "HU": "HUN", "HK": "HKG", "HN": "HND", "HM": "HMD", "VE": "VEN", "PR": "PRI", "PS": "PSE", "PW": "PLW", "PT": "PRT", "SJ": "SJM", "PY": "PRY", "IQ": "IRQ", "PA": "PAN", "PF": "PYF", "PG": "PNG", "PE": "PER", "PK": "PAK", "PH": "PHL", "PN": "PCN", "PL": "POL", "PM": "SPM", "ZM": "ZMB", "EH": "ESH", "EE": "EST", "EG": "EGY", "ZA": "ZAF", "EC": "ECU", "IT": "ITA", "VN": "VNM", "SB": "SLB", "ET": "ETH", "SO": "SOM", "ZW": "ZWE", "SA": "SAU", "ES": "ESP", "ER": "ERI", "ME": "MNE", "MD": "MDA", "MG": "MDG", "MF": "MAF", "MA": "MAR", "MC": "MCO", "UZ": "UZB", "MM": "MMR", "ML": "MLI", "MO": "MAC", "MN": "MNG", "MH": "MHL", "MK": "MKD", "MU": "MUS", "MT": "MLT", "MW": "MWI", "MV": "MDV", "MQ": "MTQ", "MP": "MNP", "MS": "MSR", "MR": "MRT", "IM": "IMN", "UG": "UGA", "TZ": "TZA", "MY": "MYS", "MX": "MEX", "IL": "ISR", "FR": "FRA", "IO": "IOT", "SH": "SHN", "FI": "FIN", "FJ": "FJI", "FK": "FLK", "FM": "FSM", "FO": "FRO", "NI": "NIC", "NL": "NLD", "NO": "NOR", "NA": "NAM", "VU": "VUT", "NC": "NCL", "NE": "NER", "NF": "NFK", "NG": "NGA", "NZ": "NZL", "NP": "NPL", "NR": "NRU", "NU": "NIU", "CK": "COK", "XK": "XKX", "CI": "CIV", "CH": "CHE", "CO": "COL", "CN": "CHN", "CM": "CMR", "CL": "CHL", "CC": "CCK", "CA": "CAN", "CG": "COG", "CF": "CAF", "CD": "COD", "CZ": "CZE", "CY": "CYP", "CX": "CXR", "CR": "CRI", "CW": "CUW", "CV": "CPV", "CU": "CUB", "SZ": "SWZ", "SY": "SYR", "SX": "SXM", "KG": "KGZ", "KE": "KEN", "SS": "SSD", "SR": "SUR", "KI": "KIR", "KH": "KHM", "KN": "KNA", "KM": "COM", "ST": "STP", "SK": "SVK", "KR": "KOR", "SI": "SVN", "KP": "PRK", "KW": "KWT", "SN": "SEN", "SM": "SMR", "SL": "SLE", "SC": "SYC", "KZ": "KAZ", "KY": "CYM", "SG": "SGP", "SE": "SWE", "SD": "SDN", "DO": "DOM", "DM": "DMA", "DJ": "DJI", "DK": "DNK", "VG": "VGB", "DE": "DEU", "YE": "YEM", "DZ": "DZA", "US": "USA", "UY": "URY", "YT": "MYT", "UM": "UMI", "LB": "LBN", "LC": "LCA", "LA": "LAO", "TV": "TUV", "TW": "TWN", "TT": "TTO", "TR": "TUR", "LK": "LKA", "LI": "LIE", "LV": "LVA", "TO": "TON", "LT": "LTU", "LU": "LUX", "LR": "LBR", "LS": "LSO", "TH": "THA", "TF": "ATF", "TG": "TGO", "TD": "TCD", "TC": "TCA", "LY": "LBY", "VA": "VAT", "VC": "VCT", "AE": "ARE", "AD": "AND", "AG": "ATG", "AF": "AFG", "AI": "AIA", "VI": "VIR", "IS": "ISL", "IR": "IRN", "AM": "ARM", "AL": "ALB", "AO": "AGO", "AQ": "ATA", "AS": "ASM", "AR": "ARG", "AU": "AUS", "AT": "AUT", "AW": "ABW", "IN": "IND", "AX": "ALA", "AZ": "AZE", "IE": "IRL", "ID": "IDN", "UA": "UKR", "QA": "QAT", "MZ": "MOZ"}
function InitCoPublicationsByCountry() {
    $("#chart-08-title").text("International co-publications");

    $.ajax({
        type: "get",
        url: api_urls.publications + "/_search",
        data: {source: CoPublicationsByCountryESQuery()},
        //processData: true, 
        //dataType: "jsonp",
        success: function (data) {
            var touchdowns = data.aggregations.country.buckets;
            var margin = {top: 10, right: 20, bottom: 10, left: 20},
                    width = 800 - margin.left - margin.right,
                    height = 400 - margin.top - margin.bottom;
            // We need to colorize every country based on "numberOfWhatever"
            // colors should be uniq for every value.
            // For this purpose we create palette(using min/max series-value)
            var onlyValues = touchdowns.map(function (obj) {
                return obj.doc_count;
            });
            var minValue = Math.min.apply(null, onlyValues),
                    maxValue = Math.max.apply(null, onlyValues);
            // create color palette function
            // color can be whatever you wish
            var paletteScale = d3.scale.linear()
                    .domain([minValue, maxValue])
                    .range(["#EFEFFF", "#02386F"]); // blue color


            var arrayLength = touchdowns.length;
            var dataset = {};
            var entry = {};
            for (var i = 0; i < arrayLength; i++) {
                dataset[iso3[touchdowns[i].key.toUpperCase()]] = {numberOfThings: touchdowns[i].doc_count, fillColor: paletteScale(touchdowns[i].doc_count)};
            }
            var margin = {top: 10, right: 10, bottom: 20, left: 30},
                    width = 370 - margin.left - margin.right,
                    height = 250 - margin.top - margin.bottom;
            var map = new Datamap({
                element: document.getElementById('chart-08'),
                projection: 'mercator',
                height: null,
                width: null,
                fills: {defaultFill: '#F5F5F5'},
                data: dataset,
                geographyConfig: {
                    borderColor: '#DEDEDE',
                    highlightBorderWidth: 2,
                    // don't change color on mouse hover
                    highlightFillColor: function (geo) {
                        return geo['fillColor'] || '#F5F5F5';
                    },
                    // only change border
                    highlightBorderColor: '#B7B7B7',
                    // show desired information in tooltip
                    popupTemplate: function (geo, data) {
                        // don't show tooltip if country don't present in dataset
                        if (!data) {
                            return ['<div class="hoverinfo">',
                                '<strong>', geo.properties.name, '</strong>',
                                '</div>'].join('');
                        }
                        // tooltip content
                        return ['<div class="hoverinfo">',
                            '<strong>', geo.properties.name, '</strong>',
                            '<br>Count: <strong>', data.numberOfThings, '</strong>',
                            '</div>'].join('');
                    }
                }
            })

        }});
}

function InitCoAuthorsByYear() {
    $("#chart-02-title").text("Co-authors over time");
    $.ajax({
        type: "get",
        url: api_urls.publications + "/_search",
        data: {source: CoAuthorsByYearESQuery()},
        //processData: true, 
        //dataType: "jsonp",
        success: function (data) {
            var svg = dimple.newSvg("#chart-02", 590, 400);
            var touchdowns = data.aggregations.publication_dates.buckets
            var dataSet = [];


            //NESTED OR BUILD NEW AUTHORS MAP
            var authors = [];
            for (var i = 0; i < touchdowns.length; i++) {
                for (var j = 0; j < touchdowns[i].author.buckets.length; j++) {
                    if (authors.indexOf(touchdowns[i].author.buckets[j].key) === -1) {
                        authors.push(touchdowns[i].author.buckets[j].key);
                    }
                }
            }
            $.ajax({type: "get",
                url: api_urls.authors + "/_search",
                data: {source: PersonNamesByPersonId(authors)},
                //processData: true, 
                //dataType: "jsonp",
                success: function (data) {
                    var names = {};
                    for (var i = 0; i < data.hits.hits.length; i++) {
                        names[data.hits.hits[i]["_id"]] = data.hits.hits[i]["fields"]["names.fullname"][data.hits.hits[i]["fields"]["names.fullname"].length - 1];
                    }

                    for (var i = 0; i < touchdowns.length; i++) {
                        var date = touchdowns[i].key_as_string.split("-")[0];
                        for (var j = 0; j < touchdowns[i].author.buckets.length; j++) {
                            if (touchdowns[i].author.buckets[j].key != authID) {
                                var entry = {};
                                entry.date = date;
                                entry.author = names[touchdowns[i].author.buckets[j].key];
                                entry.coauthoring_percentage = touchdowns[i].author.buckets[j].doc_count;
                                dataSet.push(entry);
                            }
                        }
                    }

                    var myChart = new dimple.chart(svg, dataSet);
                    myChart.setBounds(60, 30, 420, 330)
                    var x = myChart.addCategoryAxis("x", "date");
                    x.addOrderRule("Date");
                    myChart.addPctAxis("y", "coauthoring_percentage");
                    myChart.addSeries("author", dimple.plot.bar);
                    myChart.addLegend(600, 20, 60, 500, "Right");
                    myChart.draw();
                }

            });
        }
    });

}

function InitKeytermsByYear() {
    $("#chart-07-title").text("Keyterms over time");
    $.ajax({
        type: "get",
        url: api_urls.publications + "/_search",
        data: {source: KeytermsByYearESQuery()},
        //processData: true, 
        //dataType: "jsonp",
        success: function (data) {
            var touchdown = data.aggregations.keyterms.buckets;
            var xMin = new Date(d3.min(touchdown, function (c) {
                return d3.min(c.publication_dates.buckets, function (v) {
                    return v.key_as_string;
                });
            }));
            var xMax = new Date(d3.max(touchdown, function (c) {
                return d3.max(c.publication_dates.buckets, function (v) {
                    return v.key_as_string;
                });
            }));
            var years = xMax.getFullYear() - xMin.getFullYear();
            var minYear = xMin.getFullYear();
            var dataEntry = [];
            for (var i = minYear; i <= minYear + years; i++) {
                var zero = {"doc_count": 0, "key_as_string": ""};
                xMin.setFullYear(i);
                zero.key_as_string = xMin.toISOString().slice(0, 10);
                zero.key = xMin.getTime();
                dataEntry.push(zero);
            }

            var dataSet = [];
            for (var i = 0; i < touchdown.length; i++) {
                var entry = {}, y = [], x = [];
                entry.type = 'scatter';

                for (var j = 0; j < dataEntry.length; j++)
                {
                    var temp = touchdown[i].publication_dates.buckets.filter(function (e) {
                        return new Date(dataEntry[j].key_as_string).getTime() == e.key;
                    })
                    if (temp[0])
                        y.push(temp[0].doc_count)
                    else
                        y.push(0);
                    x.push(dataEntry[j].key_as_string);
                }
                entry.x = x
                entry.y = y;
                entry.fill = 'tonexty';
                entry.xaxis = "x";
                entry.legendgroup = touchdown[i].key;
                entry.name = touchdown[i].key;
                entry.yaxis = "y";
                dataSet.push(entry);
            }

            var layout = {
                legend: {font: {
      family: 'sans-serif',
      size: 9,
      color: '#000'
    }},
                width: 600,
                                height: 400,xaxis: {anchor: "y", gridcolor: "rgba(255,255,255,1)", tickcolor: "rgba(51,51,51,1)", tickfont: {
                        color: "rgba(77,77,77,1)",
                        family: "",
                        size: 11.6894977169
                    }, title: "years", titlefont: {
                        color: "rgba(0,0,0,1)",
                        family: "",
                        size: 14.6118721461
                    }},
                yaxis: {
                    anchor: "x", title: "doc_count", titlefont: {
                        color: "rgba(0,0,0,1)",
                        family: "",
                        size: 14.6118721461
                    },
                }}

            Plotly.newPlot('chart-07', dataSet, layout);

        }
    });

}


function arrayUnique(array) {
    var a = array.concat();
    for (var i = 0; i < a.length; ++i) {
        for (var j = i + 1; j < a.length; ++j) {
            if (a[i] === a[j])
                a.splice(j--, 1);
        }
    }

    return a;
}

function type(d) {
    d.frequency = +d.frequency;
    return d;
}

InitPublicationsByYear();
InitWikipediaCategories();
InitCoPublicationsByCountry();
InitCoAuthorsByYear();
InitKeytermsByYear();
