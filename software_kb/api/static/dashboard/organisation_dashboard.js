var params = {"organisationID": organisationID};

Array.prototype.contains = function (elem)
{
    for (var i in this)
    {
        if (this[i] == elem)
            return true;
    }
    return false;
}

function InitPublicationsByYear(params) {
    $("#chart-01-title").text("Documents by year");
    $("#chart-01").empty();
    $.ajax({
        type: "get",
        url: api_urls.publications + "/_search",
        data: {source: PublicationsByYearESQuery(params)},
        //processData: true,
        success: function (data) {
            var margin = {top: 10, right: 10, bottom: 50, left: 30},
                    width = 570 - margin.left - margin.right,
                    height = 350 - margin.top - margin.bottom;

            var touchdowns = data.aggregations.publication_date.buckets;

            var parseDate = d3.time.format("%Y-%m-%d").parse;


            var maxDate = new Date(touchdowns[touchdowns.length - 1].key_as_string);
            var minDate = new Date(touchdowns[0].key_as_string);
            var years = maxDate.getFullYear() - minDate.getFullYear();
            var minYear = minDate.getFullYear();
            var dataSet = [];
            for (var i = minYear; i <= minYear + years; i++) {
                minDate.setFullYear(i);
                var temp = touchdowns.filter(function (e) {
                    return new Date(e.key_as_string).getTime() == minDate.getTime()
                })

                if (!temp.length > 0)
                {
                    var zero = {"doc_count": 0, "key_as_string": ""};//et hop une injection
                    zero.key_as_string = minDate.xMin.toISOString().slice(0, 10);
                    zero.key = minDate.getTime();
                    dataSet.push(zero);
                } else
                    dataSet.push(temp[0]);

            }

//Mouseover tip
//            var tip = d3.tip()
//                    .attr('class', 'd3-tip')
//                    .offset([0, 0])
//                    .html(function (d) {
//                        return "<strong>" + d.doc_count +
//                                " Publication</strong><br>" +
//                                d.key_as_string.getFullYear() + "<br>";
//                    });

            var max = pv.max(dataSet, function (d) {
                return d.doc_count;
            }),
                    x = pv.Scale.linear(0, dataSet.length - 1).range(0, width),
                    y = pv.Scale.linear(0, max).range(0, height);

// Create the basis panel
            var vis = new pv.Panel()
                    .width(width)
                    .height(height)
                    .bottom(40)
                    .left(40)
                    .right(0)
                    .top(3);
            //.event("mouseover", pv.Behavior.tipsy({gravity: "w", fade: true}));;
            var rate = Math.floor(dataSet.length / 10);
            var rank = -1;
            // Add the X-ticks
            vis.add(pv.Rule)
                    .data(dataSet)
                    .visible(function (d) {
                        return d.key;
                    })
                    .left(function () {
                        return x(this.index);
                    })
                    .bottom(-15)
                    .height(15)
                    .strokeStyle("#33A3E1")
                    // Add the tick label
                    .anchor("right").add(pv.Label)
                    .text(function (d) {

                        if ((rank != -1) && (rank != rate)) {
                            rank++;
                            return "";
                        }

                        var date = new Date(parseInt(d.key));
                        var year = date.getYear() + 2000;
                        if (year >= 100) {
                            year = year - 100;
                        }
                        if (year === 0) {
                            year = '00';
                        } else if (year < 10) {
                            year = '0' + year;
                        }
                        rank = 0;
                        return year;
                    })
                    .textStyle("#333333")
                    .textMargin("2");
            /* Y-axis and ticks. */
            vis.add(pv.Rule)
                    .data(y.ticks(3))
                    .bottom(y)
                    .strokeStyle(function (d) {
                        d ? "rgba(128,128,128,.2)" : "#000"
                    })
                    .anchor("left").add(pv.Label)
                    .text(y.tickFormat);

// Add container panel for the chart
            vis.add(pv.Panel)
                    // Add the area segments for each entry
                    .add(pv.Area)
                    // Set-up auxiliary variable to hold state (mouse over / out) 
                    .def("active", -1)
                    // Pass the data to Protovis
                    .data(dataSet)
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
                    .interpolate("monotone")
                    // Divide the chart into "segments" (needed for interactivity)
                    .segmented(true)
                    .strokeStyle("#fff")
                    .fillStyle("#00bbde")

                    // On "mouse down", perform action, such as filtering the results...
                    .event("mousedown", function (d) {
                        var time = dataSet[this.index].key;
                        var date = new Date(parseInt(time));
                        //console.log(date);
                        //clickGraph(facetfield, facetkey, date.getFullYear(), time);
                    })

                    // Add thick stroke to the chart
                    .anchor("top").add(pv.Line)
                    .lineWidth(3)
                    .strokeStyle("#00bbde")

                    // Bind the chart to DOM element
                    .root.canvas("chart-01")
                    // And render it.
                    .render();
        }
    });
}

function InitSubStructures(params) {
    $("#chart-02-title").text("Sub Structures");
    $("#chart-02").empty();
    $.ajax({
        type: "get",
        url: api_urls.organisations + "/_search",
        data: {source: SubSructuresESQuery(params)},
        //processData: true,
        success: function (data) {
            var x = [], y = [];
            if (data.hits.hits.length > 0) {
                for (var i = 0; i < data.hits.hits.length; i++) {
                    y.push(data.hits.hits[i]._source.names[0].name);
                    x.push(data.hits.hits[i].sort[0]);
                }
                var data = [{
                        type: 'bar',
                        x: x,
                        y: y,
                        orientation: 'h'
                    }];
                var layout = {
                    margin: {
                        l: 300
                    },
                    font: {size: 10}
                };
                Plotly.newPlot('chart-02', data, layout);
                var myPlot = document.getElementById('chart-02')
                myPlot.on('plotly_click', function (data) {
                    for (var i = 0; i < data.points.length; i++) {
                        //console.log('Closest point clicked:\n\n' + data.points[i].y);
                        params.orgName = data.points[i].y;
                        getOrganisationIdByName(params);
                    }
                });
            } else {
                //$("#chart-02-title").text("Authors");
                $("#chart-02").append('<div class="keen-error" style="border-radius: 4px; color: rgb(204, 204, 204); display: block; font-family: &quot;Helvetica Neue&quot;, Helvetica, Arial, sans-serif; font-size: 21px; text-align: center; height: 300px; padding-top: 135px; width: 600px;"><span>No results to visualize</span></div>');
            }

        }
    });
}

function getOrganisationIdByName(params) {
    $.ajax({
        type: "get",
        url: api_urls.organisations + "/_search",
        data: {source: OrganisationIdByNameESQuery(params)},
        //processData: true,
        success: function (data) {
            var organisationID = data.hits.hits[0]._id;
            var url = window.location.href.substring(0, window.location.href.indexOf('?'));
            url += '?orgID=' + organisationID;
            window.location.href = url;
        }
    });


}

// clear a filter when clear button is pressed, and re-do the search
var clearfilter = function (obj) {
    var type = obj.getAttribute("rel");
    var value = obj.getAttribute("title");

    if (type == "topic")
        delete params.topic;

    obj.remove();
    InitPublicationsPerYear(params);
    InitSubStructures(params);
    InitWikipediaCategories(params);
    InitKeywordsOverTime(params);
    InitInternationalCoPublications(params);
    InitCollaborationsByYear(params);
    InitConferencesByYear(params);
}

function InitWikipediaCategories(params) {
    $("#chart-06-title").text("Wikipedia Categories");
    $("#chart-06").empty();


    $.ajax({
        type: "get",
        url: api_urls.publications + "/_search",
        data: {source: WikipideaCategoriesESQuery(params)},
        success: function (data) {
            var svg = dimple.newSvg("#chart-06", 500, 400);
            var myChart = new dimple.chart(svg, data.aggregations.category.buckets);
            myChart.setBounds(20, 10, 200, 200)
            myChart.addMeasureAxis("p", "doc_count");
            var mySeries = myChart.addSeries("key", dimple.plot.pie);
            myChart.addLegend(250, 10, 20, 200, "left");
            myChart.draw();

            d3.selectAll("path").on("click", function (d, i) {

                params.topic = d.key.replace(/_/g, '');
                $("#selected_filters").append('<li><a class="btn btn-info" title = "' + params.topic + '" rel="topic" onclick="clearfilter(this)">' + params.topic + '<i class="glyphicon glyphicon-remove"></a></li>');
                InitPublicationsByYear(params);
                InitSubStructures(params);
                InitWikipediaCategories(params);
                InitKeytermsByYear(params);
                InitInternationalCoPublications(params);
                InitCollaborationsByYear(params);
                InitConferencesByYear(params);

            });

        }
    });


}

function InitKeytermsByYear(params) {
    $("#chart-04-title").text("Keyterms");
    $("#chart-04").empty();


    $.ajax({
        type: "get",
        url: api_urls.publications + "/_search",
        data: {source: KeytermsByYearESQuery(params)},
        success: function (data) {
            var touchdown = data.aggregations.keyterm.buckets;
            var parseDate = d3.time.format("%Y-%m-%d").parse;
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
                width: 800,
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

            Plotly.newPlot('chart-04', dataSet, layout);

        }
    });


}

var iso3 = {"BD": "BGD", "BE": "BEL", "BF": "BFA", "BG": "BGR", "BA": "BIH", "BB": "BRB", "WF": "WLF", "BL": "BLM", "BM": "BMU", "BN": "BRN", "BO": "BOL", "BH": "BHR", "BI": "BDI", "BJ": "BEN", "BT": "BTN", "JM": "JAM", "BV": "BVT", "BW": "BWA", "WS": "WSM", "BQ": "BES", "BR": "BRA", "BS": "BHS", "JE": "JEY", "BY": "BLR", "BZ": "BLZ", "RU": "RUS", "RW": "RWA", "RS": "SRB", "TL": "TLS", "RE": "REU", "TM": "TKM", "TJ": "TJK", "RO": "ROU", "TK": "TKL", "GW": "GNB", "GU": "GUM", "GT": "GTM", "GS": "SGS", "GR": "GRC", "GQ": "GNQ", "GP": "GLP", "JP": "JPN", "GY": "GUY", "GG": "GGY", "GF": "GUF", "GE": "GEO", "GD": "GRD", "GB": "GBR", "GA": "GAB", "SV": "SLV", "GN": "GIN", "GM": "GMB", "GL": "GRL", "GI": "GIB", "GH": "GHA", "OM": "OMN", "TN": "TUN", "JO": "JOR", "HR": "HRV", "HT": "HTI", "HU": "HUN", "HK": "HKG", "HN": "HND", "HM": "HMD", "VE": "VEN", "PR": "PRI", "PS": "PSE", "PW": "PLW", "PT": "PRT", "SJ": "SJM", "PY": "PRY", "IQ": "IRQ", "PA": "PAN", "PF": "PYF", "PG": "PNG", "PE": "PER", "PK": "PAK", "PH": "PHL", "PN": "PCN", "PL": "POL", "PM": "SPM", "ZM": "ZMB", "EH": "ESH", "EE": "EST", "EG": "EGY", "ZA": "ZAF", "EC": "ECU", "IT": "ITA", "VN": "VNM", "SB": "SLB", "ET": "ETH", "SO": "SOM", "ZW": "ZWE", "SA": "SAU", "ES": "ESP", "ER": "ERI", "ME": "MNE", "MD": "MDA", "MG": "MDG", "MF": "MAF", "MA": "MAR", "MC": "MCO", "UZ": "UZB", "MM": "MMR", "ML": "MLI", "MO": "MAC", "MN": "MNG", "MH": "MHL", "MK": "MKD", "MU": "MUS", "MT": "MLT", "MW": "MWI", "MV": "MDV", "MQ": "MTQ", "MP": "MNP", "MS": "MSR", "MR": "MRT", "IM": "IMN", "UG": "UGA", "TZ": "TZA", "MY": "MYS", "MX": "MEX", "IL": "ISR", "FR": "FRA", "IO": "IOT", "SH": "SHN", "FI": "FIN", "FJ": "FJI", "FK": "FLK", "FM": "FSM", "FO": "FRO", "NI": "NIC", "NL": "NLD", "NO": "NOR", "NA": "NAM", "VU": "VUT", "NC": "NCL", "NE": "NER", "NF": "NFK", "NG": "NGA", "NZ": "NZL", "NP": "NPL", "NR": "NRU", "NU": "NIU", "CK": "COK", "XK": "XKX", "CI": "CIV", "CH": "CHE", "CO": "COL", "CN": "CHN", "CM": "CMR", "CL": "CHL", "CC": "CCK", "CA": "CAN", "CG": "COG", "CF": "CAF", "CD": "COD", "CZ": "CZE", "CY": "CYP", "CX": "CXR", "CR": "CRI", "CW": "CUW", "CV": "CPV", "CU": "CUB", "SZ": "SWZ", "SY": "SYR", "SX": "SXM", "KG": "KGZ", "KE": "KEN", "SS": "SSD", "SR": "SUR", "KI": "KIR", "KH": "KHM", "KN": "KNA", "KM": "COM", "ST": "STP", "SK": "SVK", "KR": "KOR", "SI": "SVN", "KP": "PRK", "KW": "KWT", "SN": "SEN", "SM": "SMR", "SL": "SLE", "SC": "SYC", "KZ": "KAZ", "KY": "CYM", "SG": "SGP", "SE": "SWE", "SD": "SDN", "DO": "DOM", "DM": "DMA", "DJ": "DJI", "DK": "DNK", "VG": "VGB", "DE": "DEU", "YE": "YEM", "DZ": "DZA", "US": "USA", "UY": "URY", "YT": "MYT", "UM": "UMI", "LB": "LBN", "LC": "LCA", "LA": "LAO", "TV": "TUV", "TW": "TWN", "TT": "TTO", "TR": "TUR", "LK": "LKA", "LI": "LIE", "LV": "LVA", "TO": "TON", "LT": "LTU", "LU": "LUX", "LR": "LBR", "LS": "LSO", "TH": "THA", "TF": "ATF", "TG": "TGO", "TD": "TCD", "TC": "TCA", "LY": "LBY", "VA": "VAT", "VC": "VCT", "AE": "ARE", "AD": "AND", "AG": "ATG", "AF": "AFG", "AI": "AIA", "VI": "VIR", "IS": "ISL", "IR": "IRN", "AM": "ARM", "AL": "ALB", "AO": "AGO", "AQ": "ATA", "AS": "ASM", "AR": "ARG", "AU": "AUS", "AT": "AUT", "AW": "ABW", "IN": "IND", "AX": "ALA", "AZ": "AZE", "IE": "IRL", "ID": "IDN", "UA": "UKR", "QA": "QAT", "MZ": "MOZ"}
function InitInternationalCoPublications(params) {
    $("#chart-08-title").text("International co-publications");
    $("#chart-08").empty();
    $.ajax({
        type: "get",
        url: api_urls.publications + "/_search",
        data: {source: CoPublicationsByCountryESQuery(params)},
        //processData: true, 
        //dataType: "jsonp",
        success: function (data) {

            var touchdowns = data.aggregations.country.buckets;
            // We need to colorize every country based on "numberOfWhatever"
            // colors should be uniq for every value.
            // For this purpose we create palette(using min/max series-value)
            var onlyValues = touchdowns.map(function (obj) {
                return obj.doc_count;
            });
            var minValue = Math.min.apply(null, onlyValues),
                    maxValue = Math.max.apply(null, onlyValues);
            var m = (maxValue - minValue) / 2;
            // create color palette function
            // color can be whatever you wish
            var paletteScale = d3.scale.linear()
                    .domain([minValue/m, maxValue/m])
                    .range(["#CCCCFF", "#02386F"]); // blue color


            var arrayLength = touchdowns.length;

            var dataset = {};
            var entry = {};
            for (var i = 0; i < arrayLength; i++) {
                dataset[iso3[touchdowns[i].key.toUpperCase()]] = {numberOfThings: touchdowns[i].doc_count, fillColor: paletteScale(touchdowns[i].doc_count/m)};
            }

            var map = new Datamap({
                element: document.getElementById('chart-08'),
                projection: 'mercator',
                height: null,
                width: null,
                fills: {defaultFill: '#F5F5F5'},
                data: dataset,
                geographyConfig: {
                    borderColor: '#DEDEDE',
                    highlightBorderWidth: 1,
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
        }
    });

}

function InitCollaborationsByYear(params) {
    $("#chart-07-title").text("Co-publications");
    $("#chart-07").empty();

    $.ajax({
        type: "get",
        url: api_urls.organisations + "/" + organisationID,
        //processData: true,
        success: function (data1) {

            var allsubstructures = data1["_source"].allrelations.map(function (a) {
                return a.organisationId;
            });
            $.ajax({type: "get",
                url: api_urls.publications + "/_search",
                data: {source: CollaborationsByYearESQuery(params)},
                //processData: true, 
                //dataType: "jsonp",
                success: function (data) {

                    var touchdowns = data.aggregations.orgs.buckets;
                    var parseDate = d3.time.format("%Y-%m-%d").parse;
                    var result = touchdowns.map(function (a) {
                        return a.key;
                    });

                    $.ajax({type: "get",
                        url: api_urls.organisations + "/_search",
                        data: {source: OrgNamesByOrgIdESQuery(result)},
                        //processData: true, 
                        //dataType: "jsonp",
                        success: function (data) {

                            var names = {};
                            for (var i = 0; i < data.hits.hits.length; i++) {
                                names[data.hits.hits[i]["_id"]] = data.hits.hits[i]["fields"]["names.name"].sort(function (a, b) {
                                    return b.length - a.length;
                                })[data.hits.hits[i]["fields"]["names.name"].length - 1];
                            }
                            var xMin = new Date(d3.min(touchdowns, function (c) {
                                return d3.min(c.publication_dates.buckets, function (v) {
                                    return v.key_as_string;
                                });
                            }));
                            var xMax = new Date(d3.max(touchdowns, function (c) {
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
                            for (var i = 0; i < touchdowns.length; i++) {
                                if (touchdowns[i].key != params.organisationID && !(allsubstructures.contains(touchdowns[i].key))) {
                                    var entry = {}, y = [], x = [];
                                    entry.type = 'bar';
                                    entry.name = names[touchdowns[i].key];
                                    for (var j = 0; j < dataEntry.length; j++) {
                                        var temp = touchdowns[i].publication_dates.buckets.filter(function (e) {
                                            return new Date(dataEntry[j].key_as_string).getTime() == e.key;
                                        });
                                        if (temp[0])
                                            y.push(temp[0].doc_count)
                                        else
                                            y.push(0);
                                        x.push(dataEntry[j].key_as_string);
                                    }
                                    entry.x = x;
                                    entry.y = y;
                                    entry.count = touchdowns[i].doc_count;
                                    dataSet.push(entry);
                                }
                            }
                            var layout = {showlegend: true,
                                legend: {"orientation": "h",font: {
      family: 'sans-serif',
      size: 10,
      color: '#000'
    }},
                                width: 800,
                                height: 600,
                                barmode: 'stack', xaxis: {anchor: "y", gridcolor: "rgba(255,255,255,1)", tickcolor: "rgba(51,51,51,1)", tickfont: {
                                        color: "rgba(77,77,77,1)",
                                        family: "",
                                        size: 11.6894977169
                                    }, title: "years", titlefont: {
                                        color: "rgba(0,0,0,1)",
                                        family: "",
                                        size: 14.6118721461
                                    }},
                                yaxis: {
                                    anchor: "x", title: "Collab_count", titlefont: {
                                        color: "rgba(0,0,0,1)",
                                        family: "",
                                        size: 14.6118721461
                                    },
                                }
                            }

                            Plotly.newPlot('chart-07', dataSet, layout);
                        }

                    });

                }
            });
        }});
}

function InitConferencesByYear(params) {
    $("#chart-09-title").text("Main conferences");
    $("#chart-09").empty();
    $.ajax({type: "get",
        url: api_urls.publications + "/_search",
        data: {source: ConferencesByYearESQuery(params)},
        //processData: true, 
        //dataType: "jsonp",
        success: function (data) {

            var touchdowns = data.aggregations.confs.buckets;
            //var parseDate = d3.time.format("%Y-%m-%d").parse;

            var xMin = new Date(d3.min(touchdowns, function (c) {
                return d3.min(c.publication_dates.buckets, function (v) {
                    return v.key_as_string;
                });
            }));
            var xMax = new Date(d3.max(touchdowns, function (c) {
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
            for (var i = 0; i < touchdowns.length; i++) {
                var entry = {}, y = [], x = [], size = [], marker = {};
//                        entry.type = 'bar';
//                        entry.name = touchdowns[i].key;
                for (var j = 0; j < dataEntry.length; j++) {
                    if (touchdowns[i].key.length > 5) {
                        var temp = touchdowns[i].publication_dates.buckets.filter(function (e) {
                            return new Date(dataEntry[j].key_as_string).getTime() == e.key;
                        });
                        if (temp[0])
                            size.push(temp[0].doc_count)
                        else
                            size.push(0);
                        y.push(touchdowns[i].key);
                        x.push(dataEntry[j].key_as_string);
                    }
                }
                marker.size = size;
                marker.sizemode = 'area';
                entry.x = x;
                entry.y = y;
                marker.sizeref = 0.01
                entry.marker = marker;
                entry.mode = 'markers';
                dataSet.push(entry);
            }

            var layout = {
                title: 'Conferences',
                showlegend: false,
                height: 400,
                width: 1220,
                margin: {
                    r: 7.30593607306,
                    t: 44.7756468798,
                    b: 50,
                    l: 600
                }
            };
            Plotly.newPlot('chart-09', dataSet, layout);
        }
    });

}


InitPublicationsByYear(params);
InitSubStructures(params);
InitWikipediaCategories(params);
InitKeytermsByYear(params);
InitInternationalCoPublications(params);
InitCollaborationsByYear(params);
InitConferencesByYear(params);



