(function () {
    $("#chart-04-title").text("Co-authors");
    $( "#chart-04-title" ).append( '<div id="view_selection" ><a href="#" id="all">All Co-authors</a> &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;<a href="#" id="topic">Co-authors By Concept</a></div>' );
    var BubbleChart, root,
            __bind = function (fn, me) {
                return function () {
                    return fn.apply(me, arguments);
                };
            };

    BubbleChart = (function () {
        function BubbleChart(data) {
            this.hide_details = __bind(this.hide_details, this);
            this.show_details = __bind(this.show_details, this);
            this.hide_topics = __bind(this.hide_topics, this);
            this.display_topics = __bind(this.display_topics, this);
            this.move_towards_topic = __bind(this.move_towards_topic, this);
            this.display_by_topic = __bind(this.display_by_topic, this);
            this.move_towards_center = __bind(this.move_towards_center, this);
            this.display_group_all = __bind(this.display_group_all, this);
            this.start = __bind(this.start, this);
            this.create_vis = __bind(this.create_vis, this);
            this.create_nodes = __bind(this.create_nodes, this);
            var max_amount;
            this.data = data;
            this.width = 800;
            this.height = 400;
            this.svgContainer = "#chart-04";

            this.tooltipWidth = 150;
            this.tooltipId = "gates_tooltip";



            $(this.svgContainer).append("<div class='tooltip' id='" + this.tooltipId + "' style='position: absolute;'></div>");
            $("#" + this.tooltipId).css("width", this.tooltipWidth);
            $("#" + this.tooltipId).hide();

            this.center = {
                x: this.width / 2,
                y: this.height / 2
            };
            this.year_centers = {};
            this.keys = Object.keys(data);
            var i = 0;
            for (var key in this.data)
            {
                this.year_centers[key] = {"x": ((i + 0.41) * this.width / (this.keys.length)), "y": this.height / 2}
                i++;
            }
            this.layout_gravity = -0.01;
            this.damper = 0.1;
            this.vis = null;
            this.nodes = [];
            this.force = null;
            this.circles = null;
            this.fill_color =
                    d3.scale.ordinal().range(["#d84b2a", "#beccae", "#7aa25c"]);
            var maxs = [];
            for (var key in this.data) {
                maxs.push(d3.max(this.data[key], function (c) {
                    return parseInt(c.doc_count);
                }));
            }
            max_amount = d3.max(maxs, function (d) {
                return parseInt(d);
            });
            this.radius_scale = d3.scale.pow().exponent(0.5).domain([0, max_amount]).range([1, 10]);
            this.create_nodes();
            this.create_vis();
        }

        BubbleChart.prototype.create_nodes = function () {
            for (var key in this.data) {
                this.data[key].forEach((function (_this) {

                    return function (d) {
                        var node;
                        node = {
                            //id: d.id,
                            radius: _this.radius_scale(parseInt(d.doc_count)),
                            value: d.doc_count,
                            name: d.key,
                            //org: d.organization,
                            group: key,
                            //year: d.start_year,
                            x: Math.random() * 900,
                            y: Math.random() * 800
                        };
                        return _this.nodes.push(node);
                    };
                })(this));
            }
            return this.nodes.sort(function (a, b) {
                return b.value - a.value;
            });
        };

        BubbleChart.prototype.create_vis = function () {
            
            var that;
            this.vis = d3.select(this.svgContainer).append("svg").attr("width", this.width).attr("height", this.height).attr("id", "svg_vis");
            this.circles = this.vis.selectAll("circle").data(this.nodes, function (d) {
                return d.name;
            });
            that = this;
            this.circles.enter().append("circle").attr("r", 0)
                    .attr("fill", (function (_this) {
                return function (d) {
                    return _this.fill_color(d.group);
                };
            })(this))
                    .attr("stroke-width", 2).attr("stroke", (function (_this) {
                return function (d) {
                    return d3.rgb(_this.fill_color(d.group)).darker();
                };
            })(this))

                    .attr("id", function (d) {
                        return "bubble_" + d.name;
                    }).on("mouseover", function (d, i) {
                return that.show_details(d, i, this);
            }).on("mouseout", function (d, i) {
                return that.hide_details(d, i, this);
            });
            return this.circles.transition().duration(2000).attr("r", function (d) {
                return d.radius;
            });
        };

        BubbleChart.prototype.charge = function (d) {
            return -Math.pow(d.radius, 2.0) / 8;
        };

        BubbleChart.prototype.start = function () {
            return this.force = d3.layout.force().nodes(this.nodes).size([this.width, this.height]);
        };

        BubbleChart.prototype.display_group_all = function () {
            this.force.gravity(this.layout_gravity).charge(this.charge).friction(0.9).on("tick", (function (_this) {
                return function (e) {
                    return _this.circles.each(_this.move_towards_center(e.alpha)).attr("cx", function (d) {
                        return d.x;
                    }).attr("cy", function (d) {
                        return d.y;
                    });
                };
            })(this));
            this.force.start();
            return this.hide_topics();
        };

        BubbleChart.prototype.move_towards_center = function (alpha) {
            return (function (_this) {
                return function (d) {
                    d.x = d.x + (_this.center.x - d.x) * (_this.damper + 0.02) * alpha;
                    return d.y = d.y + (_this.center.y - d.y) * (_this.damper + 0.02) * alpha;
                };
            })(this);
        };

        BubbleChart.prototype.display_by_topic = function () {
            this.force.gravity(this.layout_gravity).charge(this.charge).friction(0.9).on("tick", (function (_this) {
                return function (e) {
                    return _this.circles.each(_this.move_towards_topic(e.alpha)).attr("cx", function (d) {
                        return d.x;
                    }).attr("cy", function (d) {
                        return d.y;
                    });
                };
            })(this));
            this.force.start();
            return this.display_topics();
        };

        BubbleChart.prototype.move_towards_topic = function (alpha) {
            return (function (_this) {
                return function (d) {
                    var target;
                    target = _this.year_centers[d.group];
                    d.x = d.x + (target.x - d.x) * (_this.damper + 0.02) * alpha * 1.1;
                    return d.y = d.y + (target.y - d.y) * (_this.damper + 0.02) * alpha * 1.1;
                };
            })(this);
        };

        BubbleChart.prototype.display_topics = function () {
            var years, years_data, years_x = {};
            var i = 0;
            for (var key in this.data)
            {
                years_x[key] = (i + 0.5) * this.width / (this.keys.length);
                i++;
            }
            years_data = d3.keys(years_x);

            years = this.vis.selectAll(".topics").data(years_data);
            return years.enter().append("text").attr("class", "topics").attr("x", (function (_this) {
                return function (d) {
                    return years_x[d];
                };
            })(this)).attr("y", 40).attr("text-anchor", "middle").text(function (d) {
                return d;
            });
        };

        BubbleChart.prototype.hide_topics = function () {
            var years;
            return years = this.vis.selectAll(".topics").remove();
        };

        BubbleChart.prototype.show_details = function (data, i, element) {
            var content;
            //d3.select(element).attr("stroke", "black");
            content = "<span class=\"name\">Co-author:</span><span class=\"value\"> " + data.name + "</span><br/><br/>";
            content += "<span class=\"value\">" + (addCommas(data.value)) + " publications</span><br/>";
            content += "<span class=\"name\">Topic:</span><span class=\"value\"> " + data.group + "</span><br/><br/>";
            //content += "<span class=\"name\">Year:</span><span class=\"value\"> " + data.year + "</span>";
            $("#" + this.tooltipId).html(content);
            $("#" + this.tooltipId).show();
            var xOffset = -70;
            var yOffset = 10;

            var ttw = $("#" + this.tooltipId).width();
            var tth = $("#" + this.tooltipId).height();
            var wscrY = 0;
            var wscrX = 0;
            var curX = event.pageX;
            var curY = event.pageY;

            var ttleft = (curX + xOffset - $(this.svgContainer).offset().left); //? curX - ttw - xOffset*2 : curX + xOffset;
//		 if (ttleft < wscrX + xOffset){
//		 	ttleft = wscrX + xOffset;
//		 } 
            var tttop = (curY - tth - yOffset * 2 - $(this.svgContainer).offset().top); //? curY - tth - yOffset*2 : curY + yOffset;
//		 if (tttop < wscrY + yOffset){
//		 	tttop = curY + yOffset;
//		 } 
            $("#" + this.tooltipId).css('top', tttop + 'px').css('left', ttleft + 'px');
        };

        BubbleChart.prototype.hide_details = function (data, i, element) {
//            d3.select(element).attr("stroke", (function (_this) {
//                return function (d) {
//                    return d3.rgb(_this.fill_color(d.group)).darker();
//                };
//            })(this));
            return $("#" + this.tooltipId).hide();
        };

        return BubbleChart;

    })();

    root = typeof exports !== "undefined" && exports !== null ? exports : this;

    $(function () {
        var chart, render_vis;
        chart = null;
        render_vis = function (data) {
            chart = new BubbleChart(data);
            chart.start();
            return root.display_all();
        };
        root.display_all = (function (_this) {
            return function () {
                return chart.display_group_all();
            };
        })(this);
        root.display_year = (function (_this) {
            return function () {
                return chart.display_by_topic();
            };
        })(this);
        root.toggle_view = (function (_this) {
            return function (view_type) {
                if (view_type === 'topic') {
                    return root.display_year();
                } else {
                    return root.display_all();
                }
            };
        })(this);
        return $.ajax({
            type: "get",
            url: api_urls.publications+"/_search",
            data: {source: PublicationsByTopicESQuery()},
            //processData: true, 
            //dataType: "jsonp",
            success: function (data) {
                var buckets = data.aggregations.topic.buckets;
                //NESTED OR BUILD NEW AUTHORS MAP
                    var authors = [];
                    for (var i = 0; i < buckets.length; i++) {
                        for (var j = 0; j < buckets[i].authors.buckets.length; j++) {
                            if (authors.indexOf(buckets[i].authors.buckets[j].key) === -1) {
                                authors.push(buckets[i].authors.buckets[j].key);
                            }
                        }
                    }
                    
                    $.ajax({type: "get",
                url: api_urls.authors + "/_search",
                data: {source: PersonNamesByPersonId(authors)},
                //processData: true, 
                //dataType: "jsonp",
                success: function (data1) {
                    var names = {};
                    for (var i = 0; i < data1.hits.hits.length; i++) {
                        names[data1.hits.hits[i]["_id"]] = data1.hits.hits[i]["fields"]["names.fullname"][data1.hits.hits[i]["fields"]["names.fullname"].length - 1];
                    }
                var dataset = {};
                for (var i = 0; i < buckets.length; i++) {
                    var bucket = buckets[i];
                    var array = [];
                    for (var j = 0; j < bucket.authors.buckets.length; j++) {
                        if(bucket.authors.buckets[j].key != authID){
                        bucket.authors.buckets[j].key = names[bucket.authors.buckets[j].key]
                        array.push(bucket.authors.buckets[j]);
                    }
                    }
                    
                    
                    dataset[bucket.key] = array;

                }
                
                
                render_vis(dataset)
            }});
            
            }});
    });

}).call(this);