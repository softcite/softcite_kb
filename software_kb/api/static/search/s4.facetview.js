/**
 *  Functions for the search front end.
 *
 */

// now the display function
(function ($) {
    $.fn.facetview = function (options, record_metadata) {

        //$.fn.facetview.record_metadata = record_metadata;
        // and add in any overrides from the call
        // these options are also overridable by URL parameters
        // facetview options are declared as a function so they are available externally
        // (see bottom of this file)
        var url_options = $.getUrlVars();
        $.fn.facetview.options = $.extend(options, url_options);
        var options = $.fn.facetview.options;

        var mode = "";
        var fillDefaultColor = '#BC0E0E';
        var fillDefaultColorLight = '#FE9A2E';

        // ===============================================
        // functions to do with filters
        // ===============================================

        // show the filter values
        var showfiltervals = function (event) {
            event.preventDefault();
            console.log('showfiltervals');
            if ($(this).hasClass('facetview_open')) {
                $(this).children('i').replaceWith('<i class="pull-right style="top:3px;" glyphicon glyphicon-plus"></i>');
                $(this).removeClass('facetview_open');
                $('#facetview_' + $(this).attr('rel')).children('li').hide();
            } else {
                $(this).children('i').replaceWith('<i class="pull-right style="top:3px;" glyphicon glyphicon-minus"></i>');
                $(this).addClass('facetview_open');
                $('#facetview_' + $(this).attr('rel')).children('li').show();
            }
        };

        // function to perform for sorting of filters
        var sortfilters = function (event) {
            event.preventDefault();
            console.log('sortfilters');
            var sortwhat = $(this).attr('href');
            var which = 0;
            for (item in options.aggs) {
                if ('field' in options.aggs[item]) {
                    if (options.aggs[item]['field'] === sortwhat) {
                        which = item;
                    }
                }
            }
            if ($(this).hasClass('facetview_count')) {
                options.aggs[which]['order'] = 'count';
            } else if ($(this).hasClass('facetview_term')) {
                options.aggs[which]['order'] = 'term';
            } else if ($(this).hasClass('facetview_rcount')) {
                options.aggs[which]['order'] = 'reverse_count';
            } else if ($(this).hasClass('facetview_rterm')) {
                options.aggs[which]['order'] = 'reverse_term';
            }
            dosearch();
            if (!$(this).parent().parent().siblings('.facetview_filtershow').hasClass('facetview_open')) {
                $(this).parent().parent().siblings('.facetview_filtershow').trigger('click');
            }
        };

        var editfilter = function (event) {
            event.preventDefault();
            console.log('editfilter');
            var which = $(this).attr('rel');
            $('#facetview').append(getEditFilterModal(which));
            $('.facetview_removeedit').bind('click', removeedit);
            $('#facetview_dofacetedit').bind('click', dofacetedit);
            $('#facetview_editmodal').modal('show');
        };

        // trigger a search when a filter choice is clicked
        var clickfilterchoice = function (event) {
            event.preventDefault();
            console.log('clickfilterchoice');
            if ($(this).html().trim().length === 0) {
console.log('checkbox');

                if (!$(this).is(':checked')) {
                    // a checkbox is unchecked -> we remove the filter
console.log('checked');
                    $('.facetview_filterselected[href="' + $(this).attr("href") + '"]').each(function () {
                        $(this).remove();
                    });
                    options.paging.from = 0;
                } else {
                    // a checkbox is checked -> we add a filter
                    var newobj = '<a class="facetview_filterselected facetview_clear ' +
                            'btn btn-warning" rel="' + $(this).attr("rel") +
                            '" alt="remove" title="remove"' +
                            ' href="' + $(this).attr("href") + '">';
                    newobj += $(this).attr("display") + ":";
                    if ($(this).html().trim().length > 0)
                        newobj += $(this).html().replace(/\(.*\)/, '');
                    else
                        newobj += $(this).attr("href");
                    newobj += ' <i class="glyphicon glyphicon-remove"></i></a>';
                    $('#facetview_selectedfilters').append(newobj);
                    $('.facetview_filterselected').unbind('click', clearfilter);
                    $('.facetview_filterselected').bind('click', clearfilter);
                    options.paging.from = 0;
                }
                dosearch();
            } else {
                var newobj = '<a class="facetview_filterselected facetview_clear ' +
                        'btn btn-warning" rel="' + $(this).attr("rel") +
                        '" alt="remove" title="remove"' +
                        ' href="' + $(this).attr("href") + '">';
                newobj += $(this).attr("display") + ":";
                if ($(this).html().trim().length > 0)
                    newobj += $(this).html().replace(/\(.*\)/, '');
                else
                    newobj += $(this).attr("href");
                newobj += ' <i class="glyphicon glyphicon-remove"></i></a>';
                $('#facetview_selectedfilters').append(newobj);
                $('.facetview_filterselected').unbind('click', clearfilter);
                $('.facetview_filterselected').bind('click', clearfilter);
                options.paging.from = 0;
                dosearch();
            }
        };

        // clear a filter when clear button is pressed, and re-do the search
        var clearfilter = function (event) {
            event.preventDefault();
//console.log('clearfilter');
            // we need to uncheck a checkbox in case the filter has been triggered by checking a checkbox
            // href attribute is similar and can be used to select the checkbox
            var hrefValue = $(this).attr("href");
            var checkBoxElement = $('input[type="checkbox"][href="'+hrefValue+'"]');
            if (checkBoxElement) {
                checkBoxElement.removeAttr("checked");
            }
            $(this).remove();
            options.paging.from = 0;
            dosearch();
        }

        // remove the edit modal from page altogether on close (rebuilt for each filter)
        var removeedit = function (event) {
            event.preventDefault();
            console.log('removeedit');
            $('#facetview_editmodal').modal('hide');
            $('#facetview_editmodal').remove();
        }
        // update parameters and re-run the facet
        var dofacetedit = function (event) {
            event.preventDefault();
            console.log('dofacetedit');
            var which = $(this).attr('rel');

            for (truc in options.aggs[which]) {
                options.aggs[which][truc] = $(this).parent().parent().find('#input_' + truc).val();
            }

            $('#facetview_editmodal').modal('hide');
            $('#facetview_editmodal').remove();
            options.paging.from = 0;
            buildfilters();
            dosearch();
        };

        // adjust how many results are shown
        var morefacetvals = function (event) {
            event.preventDefault();
            console.log('morefacetvals');
            var morewhat = options.aggs[ $(this).attr('rel') ]
            if ('size' in morewhat) {
                var currentval = morewhat['size'];
            } else {
                var currentval = 6;
            }
            var newmore = prompt('Currently showing ' + currentval +
                    '. How many would you like instead?');
            if (newmore) {
                options.aggs[ $(this).attr('rel') ]['size'] = parseInt(newmore);
                $(this).html('show up to (' + newmore + ')');
                dosearch();
                if (!$(this).parent().parent().siblings('.facetview_filtershow').hasClass('facetview_open')) {
                    $(this).parent().parent().siblings('.facetview_filtershow').trigger('click')
                }
            }
        };

        // insert a facet range once selected
        // Work in progress
        var dofacetrange = function (event) {
            event.preventDefault();
            console.log('dofacetrange');
            var rel = $('#facetview_rangerel').html();
            var range = $('#facetview_rangechoices').html();
            var newobj = '<a class="facetview_filterselected facetview_facetrange facetview_clear ' +
                    'btn btn-warning" rel="' + rel +
                    '" alt="remove" title="remove"' +
                    ' href="' + $(this).attr("href") + '">' +
                    range + ' <i class="glyphicon glyphicon-remove"></i></a>';
            $('#facetview_selectedfilters').append(newobj);
            $('.facetview_filterselected').unbind('click', clearfilter);
            $('.facetview_filterselected').bind('click', clearfilter);
            $('#facetview_rangemodal').modal('hide');
            $('#facetview_rangemodal').remove();
            options.paging.from = 0;
            dosearch();
        }
        // remove the range modal from page altogether on close (rebuilt for each filter)
        var removerange = function (event) {
            event.preventDefault()
            console.log('removerange');
            $('#facetview_rangemodal').modal('hide')
            $('#facetview_rangemodal').remove()
        };
        // build a facet range selector
        var facetrange = function (event) {
            event.preventDefault();
            console.log('facetrange');
            $('#facetview').append(facetrangeModal);
            $('#facetview_rangemodal').append('<div id="facetview_rangerel" style="display:none;">' +
                    $(this).attr('rel') + '</div>');
            $('#facetview_rangemodal').modal('show');
            $('#facetview_dofacetrange').bind('click', dofacetrange);
            $('.facetview_removerange').bind('click', removerange);
            var values = [];
            //var valsobj = $( '#facetview_' + $(this).attr('href').replace(/\./gi,'_') );
            var valsobj = $('#facetview_' + $(this).attr('href'));
            valsobj.children('li').children('a').each(function () {
                var theDate = new Date(parseInt($(this).attr('href')));
                var years = theDate.getFullYear();
                values.push(years);
            });
            values = values.sort();
            $("#facetview_slider").slider({
                range: true,
                min: 0,
                max: values.length - 1,
                values: [0, values.length - 1],
                slide: function (event, ui) {
                    $('#facetview_rangechoices .facetview_lowrangeval').html(values[ ui.values[0] ]);
                    $('#facetview_rangechoices .facetview_highrangeval').html(values[ ui.values[1] ]);
                }
            });
            $('#facetview_rangechoices .facetview_lowrangeval').html(values[0]);
            $('#facetview_rangechoices .facetview_highrangeval').html(values[ values.length - 1]);
        };

        var setDateRange = function () {
            var day_from = 1;
            var month_from = 0;

            var values = [];
            var valsobj = $(this).parent().parent();
            valsobj.children('li').children('a').each(function () {
                var theDate = new Date(parseInt($(this).attr('href')));
                var years = theDate.getFullYear();
                values.push(years);
            });
            //values = values.sort();
            var year_from = values[0];
            if (year_from == 0) {
                year_from = 1;
            }

            var range = "";
            if ($('input[name=\"day_from\"]').val()) {
                day_from = parseInt($('input[name=\"day_from\"]').val());
            }
            if ($('input[name=\"month_from\"]').val()) {
                month_from = parseInt($('input[name=\"month_from\"]').val()) - 1;
            }
            if ($('input[name=\"year_from\"]').val()) {
                year_from = parseInt($('input[name=\"year_from\"]').val());
            }

            var day_to = 31;
            var month_to = 11;
            var year_to = values[values.length - 1];

            if ($('input[name=\"day_to\"]').val()) {
                day_to = parseInt($('input[name=\"day_to\"]').val());
            }
            if ($('input[name=\"month_to\"]').val()) {
                month_to = parseInt($('input[name=\"month_to\"]').val()) - 1;
            }
            if ($('input[name=\"year_to\"]').val()) {
                year_to = parseInt($('input[name=\"year_to\"]').val());
            }

            // TBD: we should adjust here the default last day of the month
            // based on the number of days in the month (e.g. 30 days for 11, 
            // 31 days for 10, etc.)

            range += (day_from) + '-' + (month_from + 1) + '-' + year_from;
            range += " to ";
            range += (day_to) + '-' + (month_to + 1) + '-' + year_to;

            var date_from = new Date(year_from, month_from, day_from, 0, 0, 0, 0);
            var date_to = new Date(year_to, month_to, day_to, 0, 0, 0, 0);


            var rel = $(this).attr('rel');
            var newobj = '<a class="facetview_filterselected facetview_facetrange facetview_clear ' +
                    'btn btn-warning" rel="' + rel +
                    '" alt="remove" title="remove"' +
                    ' href="' + date_from.getTime() + '_' + date_to.getTime() + '">' +
                    range + ' <i class="glyphicon glyphicon-remove"></i></a>';
            $('#facetview_selectedfilters').append(newobj);
            $('.facetview_filterselected').unbind('click', clearfilter);
            $('.facetview_filterselected').bind('click', clearfilter);
            options.paging.from = 0;
            dosearch();
        };

        // set the available filter values based on results
        var putvalsinfilters = function (data) {
            // for each filter setup, find the results for it and append them to the relevant filter
            for (var each in options.aggs) {
                $('#facetview_' + options.aggs[each]['display']).children('li').remove();

                if (options.aggs[each]['type'] == 'date') {
                    //console.log(data["facets"][ options.facets[each]['display'] ]);
                    var records = data["aggregations"][ options.aggs[each]['display'] ];
                    for (var item in records) {
                        var itemint = parseInt(item, "10");
                        var theDate = new Date(itemint);
                        var years = theDate.getFullYear();
                        var append = '<li><a class="facetview_filterchoice' +
                                '" rel="' + options.aggs[each]['field'] +
                                '" href="' + item + '" display="' + options.aggs[each]['display'] + '">' + years +
                                ' (' + addCommas(records[item]) + ')</a></li>';
                        $('#facetview_' + options.aggs[each]['display']).append(append);
                    }
                } else {
                    var records = data["aggregations"][ options.aggs[each]['display'] ];
                    var numb = 0;
                    for (var item in records) {
                        if (numb >= options.aggs[each]['size']) {
                            break;
                        }
                        var item2;
                        if (options.aggs[each]['display'] == "document_types")
                            item2 = doc_types[item];
                        else
                            item2 = item;
                        if (options.aggs[each]['display'].indexOf('class') != -1)
                            item2 = item.replace(/\s/g, '');
                        var append = '<li><a class="facetview_filterchoice' +
                                '" rel="' + options.aggs[each]['field'] + '" href="' + item + '" display="' + options.aggs[each]['display'] + '">'

                                + item2 +
                                ' (' + addCommas(records[item]) + ')</a></li>';
                        $('#facetview_' + options.aggs[each]['display']).append(append);
                        numb++;
                    }
                }
                if (!$('.facetview_filtershow[rel="' + options.aggs[each]['display'] +
                        '"]').hasClass('facetview_open')) {
                    $('#facetview_' + options.aggs[each]['display']).children("li").hide();
                }
                if ($('#facetview_visualisation_' + options.aggs[each]['display']).length > 0) {
                    $('.facetview_visualise[href=' + options.aggs[each]['display'] + ']').trigger('click');
                }
            }
            $('.facetview_filterchoice').bind('click', clickfilterchoice);
        };

        var add_facet = function (event) {
            event.preventDefault();

            var truc = {'field': 'undefined', 'display': 'new_facet', 'size': 0, 'type': '', 'view': 'hidden'};
            options.aggs.push(truc);
            buildfilters();
            dosearch();
        };

        var add_field = function (event) {
            event.preventDefault();
            var nb_fields = options['complex_fields'] + 1;
            $(this).parent().parent().append(field_complex.replace(/{{NUMBER}}/gi, '' + nb_fields)
                    .replace(/{{HOW_MANY}}/gi, options.paging.size));

            // bind the new thingies in the field
            $('#facetview_partial_match' + nb_fields).bind('click', fixmatch);
            $('#facetview_exact_match' + nb_fields).bind('click', fixmatch);
            $('#facetview_fuzzy_match' + nb_fields).bind('click', fixmatch);
            $('#facetview_match_any' + nb_fields).bind('click', fixmatch);
            $('#facetview_match_all' + nb_fields).bind('click', fixmatch);
            $('#facetview_howmany' + nb_fields).bind('click', howmany);

            $('#field_all_text' + nb_fields).bind('click', set_field);
            $('#field_software' + nb_fields).bind('click', set_field);
            $('#field_authors' + nb_fields).bind('click', set_field);
            $('#field_contexts' + nb_fields).bind('click', set_field);
            $('#field_licenses' + nb_fields).bind('click', set_field);
            $('#field_prgramming_languages' + nb_fields).bind('click', set_field);

            /*$('#lang_all' + nb_fields).bind('click', set_field);
            $('#lang_en' + nb_fields).bind('click', set_field);
            $('#lang_de' + nb_fields).bind('click', set_field);
            $('#lang_fr' + nb_fields).bind('click', set_field);*/

            $('#must' + nb_fields).bind('click', set_field);
            $('#should' + nb_fields).bind('click', set_field);
            $('#must_not' + nb_fields).bind('click', set_field);

            options['complex_fields'] = nb_fields;

            // resize the new field
            thewidth = $('#facetview_searchbar' + nb_fields).parent().width();
            $('#facetview_searchbar' + nb_fields).css('width', (thewidth / 2) - 30 + 'px');
            $('#facetview_freetext' + nb_fields).css('width', (thewidth / 2) - 30 + 'px');

            // bind the new input field with the query callback
            if (options.use_delay) {
                $('#facetview_freetext' + nb_fields).bindWithDelay('keyup', dosearch, options.freetext_submit_delay);
                $('#facetview_freetext' + nb_fields).bind('keyup', checkDisambButton);
            }
        };

        var set_field = function (event) {
            event.preventDefault();
            var theID = $(this).attr("rank");
            var labelID = $(this).attr("label");
            $('#label' + labelID + '_facetview_searchbar' + theID).empty();
            $('#label' + labelID + '_facetview_searchbar' + theID).append($(this).text());
            dosearch();
        };

        // show the add/remove filters options
        var addremovefacet = function (event) {
            event.preventDefault();
            if ($(this).hasClass('facetview_filterexists')) {
                $(this).removeClass('facetview_filterexists');
                delete options.aggs[$(this).attr('href')];
            } else {
                $(this).addClass('facetview_filterexists');
                options.aggs.push({'field': $(this).attr('title')});
            }
            buildfilters();
            dosearch();
        };
        var showarf = function (event) {
            event.preventDefault()
            $('#facetview_addremovefilters').toggle()
        };
        var addremovefacets = function () {
            $('#facetview_filters').append('<a id="facetview_showarf" href="">' +
                    'add or remove filters</a><div id="facetview_addremovefilters"></div>')
            for (var idx in options.aggs) {
                if (options.addremovefacets.indexOf(options.aggs[idx].field) == -1) {
                    options.addremovefacets.push(options.aggs[idx].field)
                }
            }
            for (var facet in options.addremovefacets) {
                var thisfacet = options.addremovefacets[facet]
                var filter = '<a class="btn '
                var index = 0
                var icon = '<i class="glyphicon glyphicon-plus"></i>'
                for (var idx in options.aggs) {
                    if (options.aggs[idx].field == thisfacet) {
                        filter += 'btn-warning facetview_filterexists'
                        index = idx
                        icon = '<i class="glyphicon glyphicon-remove"></i> '
                    }
                }
                filter += ' facetview_filterchoose" style="margin-top:5px;" href="' + index + '" title="' + thisfacet + '">' + icon + thisfacet + '</a><br />'
                $('#facetview_addremovefilters').append(filter)
            }
            $('#facetview_addremovefilters').hide();
            $('#facetview_showarf').bind('click', showarf);
            $('.facetview_filterchoose').bind('click', addremovefacet);
        };

        // pass a list of filters to be displayed
        var buildfilters = function () {
            var filters = options.aggs;
            //var thefilters = "<h3>Facets</h3>";
            var thefilters = "";

            for (var idx in filters) {
                var _filterTmpl = '<div class="row">';
                _filterTmpl += ' \
                    <div style="min-width:100%;" id="facetview_filterbuttons" class="btn-group"> \
                        <button style="text-align:left; min-width:80%;" class="facetview_filtershow btn btn-default" rel="{{FILTER_NAME}}" type="button" >\
                            <i class="pull-right glyphicon glyphicon-plus" style="top:3px;" ></i>\
                            {{FILTER_DISPLAY}}\
                        </button>\
                        <div class="btn-group" role="group">\
                            <button type="button" class="btn btn-default dropdown-toggle" data-toggle="dropdown" aria-haspopup="true" aria-expanded="false">\
                                <span class="caret"></span>\
                            </button>\
                            <ul class="dropdown-menu"> \
                              <li><a class="facetview_sort facetview_count" href="{{FILTER_EXACT}}">sort by count</a></li> \
                              <li><a class="facetview_sort facetview_term" href="{{FILTER_EXACT}}">sort by term</a></li> \
                              <li><a class="facetview_sort facetview_rcount" href="{{FILTER_EXACT}}">sort reverse count</a></li> \
                              <li><a class="facetview_sort facetview_rterm" href="{{FILTER_EXACT}}">sort reverse term</a></li> \
                              <li class="divider"></li> \
                              <li><a class="facetview_facetrange" rel="{{FACET_IDX}}" href="{{FILTER_EXACT}}">apply a filter range</a></li>{{FACET_VIS}} \
                              <li><a class="facetview_morefacetvals" rel="{{FACET_IDX}}" href="{{FILTER_EXACT}}">show up to ({{FILTER_HOWMANY}})</a></li> \
                              <li class="divider"></li> \
                              <li><a class="facetview_editfilter" rel="{{FACET_IDX}}" href="{{FILTER_EXACT}}">Edit this filter</a></li> \
                              </ul>\
                        </div>\
                    </div>\
                    <ul id="facetview_{{FILTER_NAME}}" style="margin-left:15px;" class="facetview_filters"> \
                    	';
                if (filters[idx]['type'] == 'date') {
                    _filterTmpl +=
                            '<div id="date-input" style="position:relative;margin-bottom:10px;margin-left:-10px;top:-15px;"> \
						   <input class="input-date" type="text" id="day_from" name="day_from" \
						   size="2" maxlength="2" placeholder="DD"/> \
						   <input class="input-date" type="text" id="month_from" name="month_from" size="2" maxlength="2"\
						    placeholder="MM"/> \
						   <input class="input-date" type="text" id="year_from" name="year_from" size="4" maxlength="4"\
						     placeholder="YYYY"/>\
						   To&nbsp;:&nbsp;<input class="input-date" type="text" id="day_to" name="day_to" size="2" maxlength="2" \
						    placeholder="DD"" /> \
						   <input class="input-date" type="text" id="month_to" name="month_to" size="2"  maxlength="2" \
						    placeholder="MM"/> \
					   	   <input class="input-date" type="text" id="year_to" name="year_to" size="4" maxlength="4"\
					         placeholder="YYYY"/> \
					       <div id="validate-date-range" alt="set date range" title="set date range" rel="{{FACET_IDX}}" class="glyphicon glyphicon-ok" /></div>';
                }
                _filterTmpl += '</ul>';
                _filterTmpl += '</div>';
                if (options.visualise_filters) {
                    var vis = '<li><a class="facetview_visualise" rel="{{FACET_IDX}}" href="{{FILTER_DISPLAY}}">visualise this filter</a></li>';
                    thefilters += _filterTmpl.replace(/{{FACET_VIS}}/g, vis);
                } else {
                    thefilters += _filterTmpl.replace(/{{FACET_VIS}}/g, '');
                }
                thefilters = thefilters.replace(/{{FILTER_NAME}}/g, filters[idx]['display'])
                        .replace(/{{FILTER_EXACT}}/g, filters[idx]['display']);

                if ('size' in filters[idx]) {
                    thefilters = thefilters.replace(/{{FILTER_HOWMANY}}/gi, filters[idx]['size']);
                } else {
                    // default if size is not indicated in the parameters
                    thefilters = thefilters.replace(/{{FILTER_HOWMANY}}/gi, 6);
                }
                thefilters = thefilters.replace(/{{FACET_IDX}}/gi, idx);
                if ('display' in filters[idx]) {
                    thefilters = thefilters.replace(/{{FILTER_DISPLAY}}/g, filters[idx]['display']);
                } else {
                    thefilters = thefilters.replace(/{{FILTER_DISPLAY}}/g, filters[idx]['field']);
                }
            }

            //var temp_intro = '<form class="well" id="scope_area"><label class="checkbox">' +
            //        '<input type="checkbox" name="scientific" checked>Technical content</label>';
            //temp_intro += '<label class="checkbox">' +
            //        '<input type="checkbox" name="fulltext" checked>Full text available online</label>';
            //temp_intro += '<label class="checkbox">' +
            //        '<input type="checkbox" name="scholarly">Scholarly content</label>';
            //temp_intro += '<button type="button" class="btn" data-toggle="button">Custom scope restriction</button>';
            //temp_intro += '</form>';

            //$('#facetview_filters').html("").append(temp_intro);
            //$('#scope_area').bind('click', setScope);


            $('#facetview_filters').html("").append(thefilters);
            
            options.visualise_filters ? $('.facetview_visualise').bind('click', show_vis) : "";
            $('.facetview_morefacetvals').bind('click', morefacetvals);
            $('.facetview_facetrange').bind('click', facetrange);
            $('.facetview_sort').bind('click', sortfilters);
            $('.facetview_editfilter').bind('click', editfilter);
            $('.facetview_filtershow').bind('click', showfiltervals);
            options.addremovefacets ? addremovefacets() : "";
            if (options.description) {
                $('#facetview_filters').append('<div><h3>Meta</h3>' + options.description + '</div>');
            }
            $('#validate-date-range').bind('click', setDateRange);
            $('#date-input').hide();
            
            var temp_intro = '<div class="row">\
                        <button style="text-align:left; min-width:20%;margin-top:10px;" class="btn btn-default" id="new_facet" href="" type="button" >\
                            <i class="glyphicon glyphicon-plus"></i> add new facet \
                        </button>\
                        </div>\
			';
            $('#facetview_filters').append(temp_intro);
            $('#new_facet').bind('click', add_facet);
        };

        // ===============================================
        // filter visualisations
        // ===============================================

        var show_vis = function (event) {
            event.preventDefault();
            var update = false;
            if ($('#facetview_visualisation' + '_' + $(this).attr('href')).length) {
                //$('#facetview_visualisation' + '_'+$(this).attr('href')).remove();
                update = true;
            }

            var vis;
            var indx = null;
            for (var idx in options.aggs) {
                if (options.aggs[idx]['display'] == $(this).attr('href')) {
                    indx = idx;
                    break;
                }
            }

            if (!update) {
                if ((options.aggs[idx]['type'] == 'class') || (options.aggs[idx]['type'] == 'country')) {
                    vis = '<div id="facetview_visualisation' + '_' + $(this).attr('href') + '" style="position:relative;top:5px;"> \
	                    <div class="modal-body2" id ="facetview_visualisation' + '_' + $(this).attr('href') + '_chart"> \
	                    </div> \
	                    </div>';
                } else if (options.aggs[idx]['type'] == 'entity') {
                    vis = '<div id="facetview_visualisation' + '_' + $(this).attr('href') + '" style="position:relative;"> \
	                    <div class="modal-body2" id ="facetview_visualisation' + '_' + $(this).attr('href') + '_chart"> \
	                    </div> \
	                    </div>';
                } else if (options.aggs[idx]['type'] == 'taxonomy') {
                    vis = '<div id="facetview_visualisation' + '_' + $(this).attr('href') + '" style="position:relative;top:5px;"> \
	                    <div class="modal-body2" id ="facetview_visualisation' + '_' + $(this).attr('href') + '_chart"> \
	                    </div> \
	                    </div>';
                } else if (options.aggs[idx]['type'] == 'date') {
                    vis = '<div id="facetview_visualisation' + '_' + $(this).attr('href') + '" style="position:relative;left:-10px;"> \
	                    <div class="modal-body2" id ="facetview_visualisation' + '_' + $(this).attr('href') + 
                            '_chart" style="position:relative;"> \
	                    </div> \
	                    </div>';
                } else {
                    vis = '<div id="facetview_visualisation' + '_' + $(this).attr('href') + '" style="position:relative;"> \
                        <div class="modal-body2" id ="facetview_visualisation' + '_' + $(this).attr('href') + '_chart" style="position:relative;"> \
                        </div> \
                        </div>';
                }
                vis = vis.replace(/{{VIS_TITLE}}/gi, $(this).attr('href'));
                $('#facetview_' + $(this).attr('href')).prepend(vis);
            }
            var parentWidth = $('#facetview_filters').width();

            if ((options.aggs[idx]['type'] == 'class') || (options.aggs[idx]['type'] == 'country')) {
                donut2($(this).attr('rel'), $(this).attr('href'),
                        parentWidth * 0.8, 'facetview_visualisation' + '_' + $(this).attr('href') + "_chart", update);
            } else if (options.aggs[idx]['type'] == 'date') {
                timeline($(this).attr('rel'), parentWidth * 0.75,
                        'facetview_visualisation' + '_' + $(this).attr('href') + "_chart");
                $('#date-input').show();
            } else if (options.aggs[idx]['type'] == 'taxonomy') {
                wheel($(this).attr('rel'), $(this).attr('href'), parentWidth * 0.8,
                        'facetview_visualisation' + '_' + $(this).attr('href') + "_chart", update);
            } else if (options.aggs[idx]['type'] == 'cloud') {
                cloud($(this).attr('rel'), $(this).attr('href'), parentWidth * 0.8,
                        'facetview_visualisation' + '_' + $(this).attr('href') + "_chart", update);
            }

        };

        var wheel = function (facetidx, facetkey, width, place, update) {
            var w = width,
                    h = w,
                    r = w / 2,
                    x = d3.scale.linear().range([0, 2 * Math.PI]),
                    y = d3.scale.pow().exponent(1.3).domain([0, 1]).range([0, r]),
                    p = 5,
                    duration = 1000;

            var vis = d3.select("#facetview_visualisation_" + facetkey + " > .modal-body2");
            if (update) {
                vis.select("svg").remove();
            }

            vis = d3.select("#facetview_visualisation_" + facetkey + " > .modal-body2").append("svg:svg")
                    .attr("width", w + p * 2)
                    .attr("height", h + p * 2)
                    .append("g")
                    .attr("transform", "translate(" + (r + p) + "," + (r + p) + ")");

            var partition = d3.layout.partition()
                    .sort(null)
                    .value(function (d) {
                        return 5.8 - d.depth;
                    });

            var arc = d3.svg.arc()
                    .startAngle(function (d) {
                        return Math.max(0, Math.min(2 * Math.PI, x(d.x)));
                    })
                    .endAngle(function (d) {
                        return Math.max(0, Math.min(2 * Math.PI, x(d.x + d.dx)));
                    })
                    .innerRadius(function (d) {
                        return Math.max(0, d.y ? y(d.y) : d.y);
                    })
                    .outerRadius(function (d) {
                        return Math.max(0, y(d.y + d.dy));
                    });

            //var fill = d3.scale.log(.1, 1).domain([0.005,0.1]).range(["#FF7700","#FCE6D4"]);
            var fill = d3.scale.log(.1, 1).domain([0.005, 0.1]).range(["#FCE6D4", "#FF7700"]);

            var facetfield = options.aggs[facetidx]['field'];
            var records = options.data['aggregations'][facetkey];
            var datas = [];
            var sum = 0;
            var numb = 0;
            for (var item in records) {
                if (numb >= options.aggs[facetidx]['size']) {
                    break;
                }
                var item2 = item.replace(/\s/g, '');
                var count = records[item];
                sum += count;

                var ind = item2.indexOf(".");
                if (ind != -1) {
                    // first level
                    var item3 = item2.substring(0, ind);
                    var found3 = false;
                    for (var p in datas) {
                        if (datas[p].term == item3) {
                            datas[p]['count'] += records[item];
                            found3 = true;
                            break;
                        }
                    }
                    if (!found3) {
                        datas.push({'term': item3, 'count': records[item], 'source': item, 'relCount': 0});
                    }
                    var ind2 = item2.indexOf(".", ind + 1);
                    if (ind2 != -1) {
                        //second level
                        var item4 = item2.substring(0, ind2);
                        var found4 = false;
                        for (var p in datas) {
                            if (datas[p].term == item4) {
                                datas[p]['count'] += records[item];
                                found4 = true;
                                break;
                            }
                        }
                        if (!found4) {
                            datas.push({'term': item4, 'count': records[item], 'source': item, 'relCount': 0});
                        }
                        datas.push({'term': item2, 'count': records[item], 'source': item, 'relCount': 0});
                    } else {
                        var found3 = false;
                        for (var p in datas) {
                            if (datas[p].term == item3) {
                                datas[p]['count'] += records[item];
                                found3 = true;
                                break;
                            }
                        }
                        if (!found3) {
                            datas.push({'term': item3, 'count': records[item], 'source': item, 'relCount': 0});
                        }
                        datas.push({'term': item2, 'count': records[item], 'source': item, 'relCount': 0});
                    }
                } else {
                    var found2 = false;
                    for (var p in datas) {
                        if (datas[p].term == item2) {
                            datas[p]['count'] += records[item];
                            found2 = true;
                            break;
                        }
                    }
                    if (!found2) {
                        datas.push({'term': item2, 'count': records[item], 'source': item, 'relCount': 0});
                    }
                }
                numb++;
            }
            //console.log('wheel data:');			
            //console.log(datas);
            for (var item in datas) {
                datas[item]['relCount'] = datas[item]['count'] / sum;
            }

            //var entries = datas.sort( function(a, b) { return a.count > b.count ? -1 : 1; } );
            //var entries = datas.sort( function(a, b) { return a.name > b.name ? -1 : 1; } );
            var entries = datas;
            /*var data0 = [];
             for(var item in entries) {
             data0.push(entries[item]['count']);
             }*/

            var json = [];

            // first level
            for (var item in entries) {
                var symbol = entries[item]['term'];
                var ind = symbol.indexOf(".");
                if (ind == -1) {
                    //first level category
                    json.push({'name': symbol, 'colour': fill(entries[item]['relCount'])});
                }
            }

            //second level
            for (var item in entries) {
                //var ind = entries[item]['term'].indexOf(":");
                var ind = entries[item]['term'].indexOf(".");
                if (ind != -1) {
                    var symbol = entries[item]['term'];
                    var motherCategory = symbol.substring(0, ind);
                    for (item2 in json) {
                        if (json[item2]['name'] == motherCategory) {
                            // second level category
                            var children = [];
                            if (json[item2]['children']) {
                                children = json[item2]['children'];
                            }
                            var newSymbol = symbol.substring(ind + 1, symbol.length);
                            var ind2 = newSymbol.indexOf(".");
                            if (ind2 == -1) {
                                children.push({'name': newSymbol,
                                    'colour': fill(entries[item]['relCount'])});
                                json[item2]['children'] = children;
                            }
                            break;
                        }
                    }
                }
            }

            // third and last level
            for (var item in entries) {
                var ind = entries[item]['term'].indexOf(".");
                if (ind != -1) {
                    var symbol = entries[item]['term'];
                    var motherCategory = symbol.substring(0, ind);
                    for (item2 in json) {
                        if (json[item2]['name'] == motherCategory) {
                            var newSymbol = symbol.substring(ind + 1, symbol.length);
                            //var ind2 = newSymbol.indexOf(":");
                            var ind2 = newSymbol.indexOf(".");
                            if (ind2 != -1) {
                                var motherCategory2 = newSymbol.substring(0, ind2);
                                for (item3 in json[item2]['children']) {
                                    if (json[item2]['children'][item3]['name'] == motherCategory2) {
                                        // third level category (and last one)
                                        var children2 = [];
                                        if (json[item2]['children'][item3]['children']) {
                                            children2 = json[item2]['children'][item3]['children']
                                        }
                                        children2.push({'name': newSymbol.substring(ind2 + 1, newSymbol.length),
                                            'colour': fill(entries[item]['relCount'])});
                                        json[item2]['children'][item3]['children'] = children2;
                                        break;
                                    }
                                }
                            }
                            break;
                        }
                    }
                }
            }

            //console.log(json);
            //console.log(JSON.stringify(json,null, 2));

            var nodes = partition.nodes({children: json});
            var path = vis.selectAll("path")
                    .data(nodes);
            path.enter().append("path")
                    .attr("id", function (d, i) {
                        return "path-" + i;
                    })
                    .attr("d", arc)
                    .attr("fill-rule", "evenodd")
                    .style("fill", colour)
                    //.style("fill", function(d) { return fill(d.data); })
                    .on("click", click);

            var text = vis.selectAll("text").data(nodes);
            var textEnter = text.enter().append("text")
                    .style("fill-opacity", 1)
                    .style("fill", function (d) {
                        return brightness(d3.rgb(colour(d))) < 125 ? "#eee" : "#000";
                    })
                    .attr("text-anchor", function (d) {
                        return x(d.x + d.dx / 2) > Math.PI ? "end" : "start";
                    })
                    .attr("dy", ".2em")
                    .attr("transform", function (d) {
                        var multiline = (d.name || "").split(" ").length > 1,
                                angle = x(d.x + d.dx / 2) * 180 / Math.PI - 90,
                                rotate = angle + (multiline ? -.5 : 0);
                        return "rotate(" + rotate + ")translate(" + (y(d.y) + p) + ")rotate(" + (angle > 90 ? -180 : 0) + ")";
                    })
                    .on("click", click);
            textEnter.append("tspan")
                    .attr("x", 0)
                    .text(function (d) {
                        return d.depth ? d.name.split(" ")[0] : "";
                    });
            textEnter.append("tspan")
                    .attr("x", 0)
                    .attr("dy", "1em")
                    .text(function (d) {
                        return d.depth ? d.name.split(" ")[1] || "" : "";
                    });


            function click(d) {
                // we need to reconstitute the complete field name
                var theName = d.name;
                if (d.parent && d.parent.name) {
                    //theName = d.parent.name + ":" + theName;
                    theName = d.parent.name + "." + theName;
                    if (d.parent.parent && d.parent.parent.name) {
                        //theName = d.parent.parent.name + ":" + theName;
                        theName = d.parent.parent.name + "." + theName;
                    }
                }

                clickGraph(facetfield, facetkey, theName, theName);

                path.transition()
                        .duration(duration)
                        .attrTween("d", arcTween(d));

                // Somewhat of a hack as we rely on arcTween updating the scales.
                text
                        .style("visibility", function (e) {
                            return isParentOf(d, e) ? null : d3.select(this).style("visibility");
                        })
                        .transition().duration(duration)
                        .attrTween("text-anchor", function (d) {
                            return function () {
                                return x(d.x + d.dx / 2) > Math.PI ? "end" : "start";
                            };
                        })
                        .attrTween("transform", function (d) {
                            var multiline = (d.name || "").split(" ").length > 1;
                            return function () {
                                var angle = x(d.x + d.dx / 2) * 180 / Math.PI - 90,
                                        rotate = angle + (multiline ? -.5 : 0);
                                return "rotate(" + rotate + ")translate(" + (y(d.y) + p) + ")rotate(" + (angle > 90 ? -180 : 0) + ")";
                            };
                        })
                        .style("fill-opacity", function (e) {
                            return isParentOf(d, e) ? 1 : 1e-6;
                        })
                        .each("end", function (e) {
                            d3.select(this).style("visibility", isParentOf(d, e) ? null : "hidden");
                        });
            }

            function isParentOf(p, c) {
                if (p === c)
                    return true;
                if (p.children) {
                    return p.children.some(function (d) {
                        return isParentOf(d, c);
                    });
                }
                return false;
            }

            function colour(d) {
                if (d.children) {
                    // There is a maximum of two children!
                    var colours = d.children.map(colour),
                            a = d3.hsl(colours[0]),
                            b = d3.hsl(colours[1]);
                    // L*a*b* might be better here...
                    return d3.hsl((a.h + b.h) / 2, a.s * 1.2, a.l / 1.2);
                }
                return d.colour || "#fff";
            }

            // Interpolate the scales!
            function arcTween(d) {
                var my = maxY(d),
                        xd = d3.interpolate(x.domain(), [d.x, d.x + d.dx]),
                        yd = d3.interpolate(y.domain(), [d.y, my]),
                        yr = d3.interpolate(y.range(), [d.y ? 20 : 0, r]);
                return function (d) {
                    return function (t) {
                        x.domain(xd(t));
                        y.domain(yd(t)).range(yr(t));
                        return arc(d);
                    };
                };
            }

            function maxY(d) {
                return d.children ? Math.max.apply(Math, d.children.map(maxY)) : d.y + d.dy;
            }

            // http://www.w3.org/WAI/ER/WD-AERT/#color-contrast
            function brightness(rgb) {
                return rgb.r * .299 + rgb.g * .587 + rgb.b * .114;

            }
        };

        var donut2 = function (facetidx, facetkey, width, place, update) {
            var vis = d3.select("#facetview_visualisation_" + facetkey + " > .modal-body2");

            var facetfield = options.aggs[facetidx]['field'];
            var records = options.data['aggregations'][facetkey];
            if (records.length === 0) {
                $('#' + place).hide();
                return;
            } else {
                var siz = 0;
                for (var item in records) {
                    siz++;
                }
                if (siz === 0) {
                    $('#' + place).hide();
                    return;
                }
            }
            $('#' + place).show();

            var data2 = [];
            var sum = 0;
            var numb = 0;
            for (var item in records) {
                if (records[item] > 0) {

                    if (numb >= options.aggs[facetidx]['size']) {
                        break;
                    }

                    var item2 = item.replace(/\s/g, '');
                    var count = records[item];
                    sum += count;
                    
                    if(facetkey == "document_types")
                    data2.push({'term': doc_types[item2], 'count': records[item], 'source': doc_types[item], 'relCount': 0});
                else 
                    data2.push({'term': item2, 'count': records[item], 'source': item, 'relCount': 0});
                    numb++;
                }
            }

            for (var item in data2) {
                if (data2[item]['count'] > 0) {
                    data2[item]['relCount'] = data2[item]['count'] / sum;
                }
            }

            var data = data2;
            var entries = data.sort(function (a, b) {
                return a.count < b.count ? -1 : 1;
            });

            var data0 = [];
            for (var item in entries) {
                data0.push(entries[item]['relCount']);
            }

            var height = width * 0.75,
                    outerRadius = Math.min(width, height) / 2,
                    innerRadius = outerRadius * .2,
                    n = data0.length,
                    q = 0,
                    //color = d3.scale.log(.1, 1).range(["#FF7700","#FCE6D4"]),
                    //color = d3.scale.log(.01, .9).range(["#FF7700","#FCE6D4"]),
                    arc = d3.svg.arc(),
                    //fill = d3.scale.log(.1, 1).domain([0.1,0.9]).range(["#FF7700","#FCE6D4"]);
                    fill = d3.scale.log(.1, 1).domain([0.1, 0.9]).range([fillDefaultColor, fillDefaultColorLight]);

            //fill = d3.scale.log(.1, 1).range(["#FF7700","#FCE6D4"]),
            donute = d3.layout.pie().sort(null);

            if (update) {
                vis.selectAll("svg").remove();
            }

            var data_arc = arcs(data0);
            vis.append("svg:svg")
                    .attr("width", width)
                    .attr("height", height)
                    .selectAll("g.arc")
                    //.data(arcs(data0))
                    .data(data_arc)
                    .enter()
                    .append("g")
                    .attr("class", "arc")
                    .attr("transform", "translate(" + (outerRadius * 1.3) + "," + outerRadius + ")")
                    .attr("index", function (d) {
                        return d.index;
                    })
                    .on("mousedown", function (d) {
                        var index = this.getAttribute("index");
                        var term = entries[index].term;
                        var source = entries[index].source;
                        if (source)
                            clickGraph(facetfield, facetkey, term, source);
                        else
                            clickGraph(facetfield, facetkey, facetfield, term, term);
                    })
                    .append("path")
                    //.attr("fill", function(d, i) { return color(entries[i]['relCount']); })
                    .style("fill", function (d) {
                        return fill(d.data);
                    })
                    .attr("stroke", "#fff")
                    .attr("d", arc);

            // we need to re-create all the arcs for placing the text labels, so that the labels
            // are not covered by the arcs
            // we also enlarge the svg area for the labels so that they are not cut
            var text = vis.select("svg")
                    .append("svg:svg")
                    .attr("width", width * 1.2)
                    .attr("height", height * 1.2)
                    .selectAll("g")
                    .data(data_arc)
                    .enter()
                    .append("g")
                    .attr("class", "arc")
                    .attr("transform", "translate(" + (outerRadius * 1.30) + "," + outerRadius + ")")
                    .append("text")
                    .attr("class", "labels")
                    .attr("transform", function (d) {
                        d.innerRadius = innerRadius;
                        d.outerRadius = outerRadius * 1.30;
                        return "translate(" + arc.centroid(d) + ")";
                    })
                    .attr('text-anchor', 'middle')
                    .text(function (d) {
                        return d.term
                    })
                    .style("textStyle", "black")
                    .style("font", "09pt sans-serif")
                    .attr("index", function (d) {
                        return d.index;
                    })
                    .on("mousedown", function (d) {
                        var index = this.getAttribute("index")
                        var term = entries[index].term;
                        var source = entries[index].source;
                        if (source)
                            clickGraph(facetfield, facetkey, term, source);
                        else
                            clickGraph(facetfield, facetkey, facetfield, term, term);
                    });

            // Store the currently-displayed angles in this._current.
            // Then, interpolate from this._current to the new angles.
            function arcTween(a) {
                var i = d3.interpolate(this._current, a);
                this._current = i(0);
                return function (t) {
                    return arc(i(t));
                };
            }

            function arcs(data0) {
                var arcs0 = donute(data0),
                        i = -1,
                        arc;
                while (++i < n) {
                    arc = arcs0[i];
                    arc.innerRadius = innerRadius;
                    arc.outerRadius = outerRadius;
                    arc.next = arcs0[i];
                    arc.term = entries[i]['term'];
                    arc.index = i;
                }
                return arcs0;
            }

            function swap() {
                d3.selectAll("g.arc > path")
                        .data(++q & 1 ? arcs(data0, data1) : arcs(data1, data0))
                        .each(transitionSplit);
            }

            // 1. Wedges split into two rings.
            function transitionSplit(d, i) {
                d3.select(this)
                        .transition().duration(1000)
                        .attrTween("d", tweenArc({
                            innerRadius: i & 1 ? innerRadius : (innerRadius + outerRadius) / 2,
                            outerRadius: i & 1 ? (innerRadius + outerRadius) / 2 : outerRadius
                        }))
                        .each("end", transitionRotate);
            }

            // 2. Wedges translate to be centered on their final position.
            function transitionRotate(d, i) {
                var a0 = d.next.startAngle + d.next.endAngle,
                        a1 = d.startAngle - d.endAngle;
                d3.select(this)
                        .transition().duration(1000)
                        .attrTween("d", tweenArc({
                            startAngle: (a0 + a1) / 2,
                            endAngle: (a0 - a1) / 2
                        }))
                        .each("end", transitionResize);
            }

            // 3. Wedges then update their values, changing size.
            function transitionResize(d, i) {
                d3.select(this)
                        .transition().duration(1000)
                        .attrTween("d", tweenArc({
                            startAngle: d.next.startAngle,
                            endAngle: d.next.endAngle
                        }))
                        .each("end", transitionUnite);
            }

            // 4. Wedges reunite into a single ring.
            function transitionUnite(d, i) {
                d3.select(this)
                        .transition().duration(1000)
                        .attrTween("d", tweenArc({
                            innerRadius: innerRadius,
                            outerRadius: outerRadius
                        }));
            }

            function tweenArc(b) {
                return function (a) {
                    var i = d3.interpolate(a, b);
                    for (var key in b)
                        a[key] = b[key]; // update data
                    return function (t) {
                        return arc(i(t));
                    };
                };
            }
        };

        var timeline = function (facetidx, width, place) {
            var facetkey = options.aggs[facetidx]['display'];
            var facetfield = options.aggs[facetidx]['field'];

            // Set-up the data
            var entries = options.data.aggregations3[facetkey];
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
                    .width(w)
                    .height(h+10)
                    .bottom(40)
                    .left(0)
                    .right(0)
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

            // Add container panel for the chart
            vis.add(pv.Panel)
                    // Add the area segments for each entry
                    .add(pv.Area)
                    // Set-up auxiliary variable to hold state (mouse over / out) 
                    .def("active", -1)
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
                    .event("mousedown", function (d) {
                        var time = entries[this.index].key;
                        var date = new Date(parseInt(time));
                        clickGraph(facetfield, facetkey, date.getFullYear(), time);
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

        var cloud = function (facetidx, facetkey, width, place, update) {

            var facetkey = options.aggs[facetidx]['display'];
            var facetfield = options.aggs[facetidx]['field'];
            var aggs = options.data['aggregations'][facetkey];
            var wordset = [];
            var vis = d3.select("#facetview_visualisation_" + facetkey + " > .modal-body2");
            if (update) {
                vis.selectAll("svg").remove();
            }

            var numb = 0;
            var max_count = 0;
            for (var fct in aggs) {
                if (numb >= options.aggs[facetidx]['size']) {
                    break;
                }
                if (aggs[fct] > max_count)
                    max_count = aggs[fct];
                numb++;
            }

            numb = 0;
            for (var fct in aggs) {
                if (numb >= options.aggs[facetidx]['size']) {
                    break;
                }
                wordset.push({'text':fct, 'size':aggs[fct]});
                numb++;
            }
            //$('#' + place).show();
            var fill = d3.scale.category20();
            var w = width;
            var h = w;
            var svg = d3.select("#facetview_visualisation_" + facetkey + " > .modal-body2").append("svg")
                        .attr("width", w*1.2)
                        .attr("height", h)
                        .append("g")
                        .attr("transform", "translate("+w/2+","+h/2+")");
            update(31);
            function update(maxRange) {
                var minRange = 10;
                if (maxRange < minRange)
                    minRange = maxRange-1;
                if (minRange == 0)
                    minRange = 1;
                var theScale = d3.scale.linear().domain([0,max_count]).range([minRange, maxRange]);            
                d3.layout.cloud().size([w*1.3, h*1.3])
                    .words(wordset.map(function(d) {
                        return {text: d.text, size: Math.floor(theScale(d.size))};
                    }))
                    //.padding(5)
                    .rotate(function () { return 0; })
                    //.rotate(function() { return ~~(Math.random() * 2) * 90; })
                    .fontSize(function (d) { return d.size; })
                    //.on("end", draw)
                    .on("end", function(output) {
                        if ( (wordset.length !== output.length) && (maxRange > 14) ) { 
                            //console.log("Recurse! " + maxRange); 
                            update(maxRange-5); 
                            return undefined;  
                        } else { 
                            draw(output); 
                        }
                    })
                    .start();
            }

            function draw(words) {
                //console.log(words); 

                var cloud = svg.selectAll("g text")
                        .data(words, function(d) { return d.text; });

                cloud.enter().append("text")
                        .style("font-size", function (d) {
                            return d.size + "px";
                        })
                        .style("fill", function (d, i) {
                            return fill(i);
                        })
                        .attr("text-anchor", "middle")
                        .attr("transform", function (d) {
                            return "translate(" + [d.x, d.y] + ")";
                        })
                        .text(function (d) {
                            return d.text;
                        }).on("click", function (d) {
                    clickGraph(facetfield, facetkey, d.text, d.text);
                });
            }

        };
        
        // normal click on a graphical facet
        var clickGraph = function (facetfield, facetKey, facetValueDisplay, facetValue) {
            var newobj = '<a class="facetview_filterselected facetview_clear ' +
                    'btn btn-warning" rel="' + facetfield +
                    '" alt="remove" title="remove"' +
                    ' href="' + facetValue + '">' +
                    facetKey + ":" + facetValueDisplay + ' <i class="glyphicon glyphicon-remove"></i></a>';
            $('#facetview_selectedfilters').append(newobj);
            $('.facetview_filterselected').unbind('click', clearfilter);
            $('.facetview_filterselected').bind('click', clearfilter);
            options.paging.from = 0;
            dosearch();
            //$('#facetview_visualisation'+"_"+facetkey).remove();
        };

        // ===============================================
        // building results
        // ===============================================
        // decrement result set
        var decrement = function (event) {
            event.preventDefault();
            if ($(this).html() != '..') {
                options.paging.from = options.paging.from - options.paging.size;
                options.paging.from < 0 ? options.paging.from = 0 : "";
                dosearch();
            }
        };

        // increment result set
        var increment = function (event) {
            event.preventDefault();
            if ($(this).html() != '..') {
                options.paging.from = parseInt($(this).attr('href'));
                $('html, body').animate({scrollTop: 0}, 'slow');
                dosearch();
            }
        };

        // write the metadata to the page
        var putmetadata = function (data) {
            $('#results_summary').empty();

            $('#results_summary').append("<p style='color:grey;'>"
                    + addCommas("" + data.found.value) + " results - in " + Math.floor(data.took)
                    + " ms (server time)</p>");

            if (typeof (options.paging.from) != 'number') {
                options.paging.from = parseInt(options.paging.from);
            }
            if (typeof (options.paging.size) != 'number') {
                options.paging.size = parseInt(options.paging.size);
            }

            var metaTmpl = ' \
              <nav> \
                <ul class="pager"> \
                  <li class="previous"><a id="facetview_decrement" style="color:#d42c2c;" href="{{from}}">&laquo; back</a></li> \
                  <li class="active"><a style="color:#d42c2c;">{{from}} &ndash; {{to}} of {{total}}</a></li> \
                  <li class="next"><a id="facetview_increment" style="color:#d42c2c;" href="{{to}}">next &raquo;</a></li> \
                </ul> \
              </nav> \
              ';

            $('#facetview_metadata').html("Not found...");
            if (data.found) {
                var from = options.paging.from + 1;
                var size = options.paging.size;
                !size ? size = 10 : "";
                var to = options.paging.from + size;
                data.found.value < to ? to = data.found.value : "";
                var meta = metaTmpl.replace(/{{from}}/g, from);
                meta = meta.replace(/{{to}}/g, to);
                meta = meta.replace(/{{total}}/g, addCommas("" + data.found.value));
                $('#facetview_metadata').html("").append(meta);
                $('#facetview_decrement').bind('click', decrement);
                from < size ? $('#facetview_decrement').html('..') : "";
                $('#facetview_increment').bind('click', increment);
                data.found.value <= to ? $('#facetview_increment').html('..') : "";
            }
        };

        // put the results on the page
        showresults = function (sdata) {
            // get the data and parse from elasticsearch or other 
            var data = null;
            if (options.search_index == "elasticsearch") {
                // default is elasticsearch
                data = parseresultsElasticSearch(sdata);
            } else {
                // nothing to do :(
                return;
            }
            options.data = data;

            // put result metadata on the page
            putmetadata(data);
            // put the filtered results on the page
            $('#facetview_results').html("");
            //var infofiltervals = new Array();
            $.each(data.records, function (index, value) {
                // write them out to the results div
                //$('#facetview_results').append( buildrecord(index) );
                buildrecord(index, $('#facetview_results'));

                $('#facetview_results tr:last-child').linkify();
                //Handle the chevron on every action.
                $("#abstract_keywords_" + index).on('shown.bs.collapse', function () {
                    $('#button_abstract_keywords_collapse_' + index).find('span').addClass('glyphicon-chevron-up').removeClass('glyphicon-chevron-down');
                });

                $("#abstract_keywords_" + index).on('hidden.bs.collapse', function () {
                    $('#button_abstract_keywords_collapse_' + index).find('span').addClass('glyphicon-chevron-down').removeClass('glyphicon-chevron-up');
                });
            });
            MathJax.Hub.Queue(["Typeset", MathJax.Hub]);
            // change filter options
            putvalsinfilters(data);

            // for the first time we visualise the filters as defined in the facet options
            for (var each in options.aggs) {
                if (options.aggs[each]['view'] == 'graphic') {
                    //if ($('.facetview_filterselected[rel=' + options.facets[each]['field'] + "]" ).length == 0 )
                    if ($('#facetview_visualisation_' + options.aggs[each]['display'] + '_chart').length == 0)
                        $('.facetview_visualise[href=' + options.aggs[each]['display'] + ']').trigger('click');
                } else if ((!$('.facetview_filtershow[rel=' + options.aggs[each]['display'] +
                        ']').hasClass('facetview_open'))
                        && (options.aggs[each]['view'] == 'textual')) {
                    $('.facetview_filtershow[rel=' + options.aggs[each]['display'] + ']').trigger('click');
                }
            }



        };

        // ===============================================
        // disambiguation
        // ===============================================

        var disambiguateNERD = function () {
            var thenum = $(this).attr("id").match(/\d+/)[0] // "3"
            var queryText = $('#facetview_freetext' + thenum).val();
//console.log($('#disambiguation_panel').children().length > 0);
            // note: the action bellow prevents the user to refine his search and disambigation
            /*if ($('#disambiguation_panel').children().length > 0)
                $('#disambiguation_panel').empty();
            else*/
            doexpandNERD(queryText);
            // take out focus after button release
            $('#disambiguate'+(thenum)).blur();
        };

        // call the NERD service and propose senses to the user for his query
        var doexpandNERD = function (queryText) {
            //var queryString = '{ "text" : "' + encodeURIComponent(queryText) +'", "shortText" : true }';
            var queryString = '{ "text" : "' + queryText + '", "shortText" : true, "language": {"lang": "en"} }';

            var urlNERD = "http://" + options.host_nerd;
            if (urlNERD.endsWith("/"))
                urlNERD = urlNERD.substring(0,urlNERD.length()-1);
            if ((!options.port_nerd) || (options.port_nerd.length == 0))
                urlNERD += options.port_nerd + "/nerd/processERDSearchQuery";
            else
                urlNERD += ":" + options.port_nerd + "/nerd/processERDSearchQuery";
            $.ajax({
                type: "POST",
                url: urlNERD,
        //              contentType: 'application/json',
        //              contentType: 'charset=UTF-8',
        //              dataType: 'jsonp',
                dataType: "text",
        //              data: { text : encodeURIComponent(queryText) },
                data: queryString,
        //              data: JSON.stringify( { text : encodeURIComponent(queryText) } ),
                success: showexpandNERD
            });
        };

        var showexpandNERD = function (sdata) {
            if (!sdata) {
                return;
            }

            var jsonObject = parseDisambNERD(sdata);

            piece = getPieceShowexpandNERD(jsonObject);
            $('#disambiguation_panel').html(piece);
        //            $('#close-disambiguate-panel').bind('click', function () {
        //                $('#disambiguation_panel').hide();
        //            })

            // we need to bind the checkbox...
            for (var sens in jsonObject['entities']) {
                $('input#selectEntity' + sens).bind('change', $.fn.facetview,clickfilterchoice);
            }

            $('#disambiguation_panel').show();
        };

        // execute a search
        var dosearch = function () {

            // make the search query
            if (options.search_index == "elasticsearch") {
                $.ajax({
                    //type: "get",
                    type: "post",
                    url: options.es_host+"/"+options.fulltext_index+"/_search?",
                    //data: {source: elasticSearchSearchQuery()},
                    data: elasticSearchSearchQuery(),
                    // processData: false,
                    //dataType: "jsonp",
                    dataType: "json",
                    contentType: "application/json",
                    success: function (data) {
                        showresults(data);
                    }
                });
            }

        };

        // adjust how many results are shown
        var howmany = function (event) {
            event.preventDefault();
            var newhowmany = prompt('Currently displaying ' + options.paging.size +
                    ' results per page. How many would you like instead?');
            if (newhowmany) {
                options.paging.size = parseInt(newhowmany);
                options.paging.from = 0;
                $('#facetview_howmany').html('results per page (' + options.paging.size + ')');
                dosearch();
            }
        };

        // what to do when ready to go
        var whenready = function () {
            //$("#facetview_presentation").remove();
            // append the facetview object to this object
            
            /*var facetview_howmany = $("#facetview_howmany").text();
            facetview_howmany = facetview_howmany.replace(/{{HOW_MANY}}/gi, options.paging.size);
            $("#facetview_howmany").text(facetview_howmany);
            //$(obj).append(thefacetview);
            // setup search option triggers
            $('#facetview_partial_match').bind('click', fixmatch);
            $('#facetview_exact_match').bind('click', fixmatch);
            $('#facetview_fuzzy_match').bind('click', fixmatch);
            $('#facetview_match_any').bind('click', fixmatch);
            $('#facetview_match_all').bind('click', fixmatch);
            $('#facetview_howmany').bind('click', howmany);*/


            // resize the searchbar
            //var thewidth = $('#facetview_searchbar').parent().width();
            //$('#facetview_searchbar').css('width', thewidth / 2 + 70 + 'px'); // -50
            //$('#facetview_freetext').css('width', thewidth / 2 + 32 + 'px'); // -88


            //$('#harvest').hide();

            // check paging info is available
            !options.paging.size ? options.paging.size = 10 : "";
            !options.paging.from ? options.paging.from = 0 : "";

            // set any default search values into the search bar
//            $('#facetview_freetext').val() == "" && options.q != "" ? $('#facetview_freetext').val(options.q) : ""

            // append the filters to the facetview object
            buildfilters();

            //obj = $(this);
            if (options.use_delay) {
                $('#facetview_freetext1').bindWithDelay('keyup', dosearch, options.freetext_submit_delay);
                $('#facetview_freetext1').bind('keyup', checkDisambButton);
            }

            // trigger the search once on load, to get all results
            //if (options.use_delay)
                dosearch();
        };

        $('#disambiguation_panel').hide();

        var searchbar = '<div id="facetview_searchbar{{NUMBER}}" style="width:100%;padding-right:0px;" class="row input-group clonedDiv">\
<div class="btn-group">\
<button id="selected-tei-field{{NUMBER}}" class=" btn btn-default dropdown-toggle" style="width:200px" data-toggle="dropdown" >\
all fields <span class="caret"></span>\
</button>\
<ul class="dropdown-menu tei-fields">\
<li><a href="#">all fields</a></li>\
<li><a href="#">software</a></li>\
<li><a href="#">authors</a></li>\
<li><a href="#">mentions</a></li>\
<li><a href="#">licenses</a></li>\
<li><a href="#">programming_language</a></li>\
</ul>\
</div>\
<div class="btn-group">\
<button id="selected-bool-field{{NUMBER}}" class="selected-bool-field btn btn-default dropdown-toggle" style="width:80px" data-toggle="dropdown">\
must <span class="caret"></span>\
</button>\
<ul class="dropdown-menu bool-fields">\
<li><a href="#">should</a></li>\
<li><a href="#">must</a></li>\
<li><a href="#">must_not</a></li>\
</ul>\
</div>\
<div style="min-width: 300px;" class="btn-group">\
<input type="text" class="form-control" id="facetview_freetext{{NUMBER}}" name="q" value="" aria-describedby="sizing-addon1" placeholder="search term" autofocus />\
</div>\
<div class="btn-group">\
<button type="button" class="btn btn-default dropdown-toggle" data-toggle="dropdown" aria-haspopup="true" aria-expanded="false">\
<span class="glyphicon glyphicon-cog"></span>\
<span class="caret"></span></button>\
<ul class="dropdown-menu">\
<li><a id="facetview_partial_match" href="">partial match</a></li>\
<li><a id="facetview_exact_match" href="">exact match</a></li>\
<li><a id="facetview_fuzzy_match" href="">fuzzy match</a></li>\
<li><a id="facetview_match_all" href="">match all</a></li>\
<li><a id="facetview_match_any" href="">match any</a></li>\
<li><a href="#">clear all</a></li>\
<li class="divider"></li>\
<li><a target="_blank" href="http://lucene.apache.org/java/2_9_1/queryparsersyntax.html">query syntax doc.</a></li>\
<li class="divider"></li>\
<li><a id="facetview_howmany" href="#">results per page ({{HOW_MANY}})</a></li>\
</ul>\
<button type="button" id="disambiguate{{NUMBER}}" class="btn btn-default" disabled="true">Disambiguate</button>\
</div>\
<div class="btn-group" style="margin-left:20px;">\
<button class="btn btn-default" id="facetview_fieldbuttons{{NUMBER}}" href="" type="button"><i class="glyphicon glyphicon-plus" style="vertical-align:middle;margin-right:0px;margin-bottom:2px;"></i></button>\
</div>\
<div class="btn-group">\
<button class="btn btn-default" id="close-searchbar{{NUMBER}}" href="" type="button"><i class="glyphicon glyphicon-minus" style="vertical-align:middle;margin-right:0px;margin-bottom:4px;"></i></button>\
</div>\
</div>';


        var keyPress = function (e) {

            // get this object
            obj = $(this);
            options.q = $(this).val();
            var thenum = $(this).attr("id").match(/\d+/)[0]; // "3"
            if (options.q)
                activateDisambButton(thenum);
            else
                deactivateDisambButton(thenum);
            //if (e.keyCode == 13 && (options.q || $("#facetview_selectedfilters").children().length > 0)) {
            if (e.keyCode == 13) 
            {
//                    if (url_options.mode)
//                        window.location.href = window.location.href.replace(/[\&#].*|$/, "&q=" + options.q);
//                    else
//                        window.location.href = window.location.href.replace(/[\?#].*|$/, "?q=" + options.q);
//
//                    options.q = unescape(options.q);
//                    activateDisambButton();
//                    $("#facetview_freetext").text(options.q);
                // check for remote config options, then do first search
                /*if (options.config_file) {
                    $.ajax({
                        type: "get",
                        url: options.config_file,
                        //dataType: "jsonp",
                        success: function (data) {
                            options = $.extend(options, data);
                            whenready();
                        },
                        error: function () {
                            $.ajax({
                                type: "get",
                                url: options.config_file,
                                success: function (data) {
                                    options = $.extend(options, $.parseJSON(data));
                                    whenready();
                                },
                                error: function () {
                                    whenready();
                                }
                            });
                        }
                    });
                } else {*/
                    //whenready();
                if ($('#facetview_filters').children().length == 0)
                    whenready();
                else
                    dosearch();
                //}
            }
        }


        // ===============================================
        // now create the plugin on the page
        return $(document).ready(function (e) {

            $("#facetview_searchbars").append(searchbar.replace(/{{NUMBER}}/gi, "1"));
            $('#close-searchbar1').hide();
            if (!options.use_delay)
                $("#facetview_freetext1").keyup(keyPress);
            $('#disambiguate1').click(disambiguateNERD);
            
            $("#facetview_fieldbuttons1").on("click", function () {
                var cloneIndex = $(".clonedDiv").length + 1;
                $("#facetview_searchbars").append(searchbar.replace(/{{NUMBER}}/gi, cloneIndex));
                $('#facetview_fieldbuttons'+cloneIndex).hide();
                $("#close-searchbar"+cloneIndex).css("display", "block");
                
                $(".tei-fields li a").click(function () {
                    var selText = $(this).text();
                    $(this).parents('.btn-group').find('.dropdown-toggle').html(selText + ' <span class="caret"></span>');
                });
                $(".lang-fields li a").click(function () {
                    var selText = $(this).text();
                    $(this).parents('.btn-group').find('.dropdown-toggle').html(selText + ' <span class="caret"></span>');
                });
                $(".bool-fields li a").click(function () {
                    var selText = $(this).text();
                    $(this).parents('.btn-group').find('.dropdown-toggle').html(selText + ' <span class="caret"></span>');
                });

                if (!options.use_delay)
                    $("#facetview_freetext" + cloneIndex).keyup(keyPress);

                $('#disambiguate' + cloneIndex).click(disambiguateNERD);

                $('#close-searchbar'+cloneIndex).click(function () {
                    // grab the index number 
                    var theIndex = $(this).attr("id").match(/\d+/)[0];
                    // remove searchbar
                    $('#facetview_searchbar'+theIndex).remove();
                    // trigger a new search if the corresponding free field is not empty and whenready has instanciated the filter facetviews
                    if (($('#facetview_freetext'+theIndex).val() != "")  && ($('#facetview_filters').children().length > 0))
                        dosearch();
                });
                cloneIndex++;
            });
            

            $(".tei-fields li a").click(function () {
                var selText = $(this).text();
                $(this).parents('.btn-group').find('.dropdown-toggle').html(selText + ' <span class="caret"></span>');
            });
            $(".lang-fields li a").click(function () {
                var selText = $(this).text();
                $(this).parents('.btn-group').find('.dropdown-toggle').html(selText + ' <span class="caret"></span>');
            });
            $(".bool-fields li a").click(function () {
                var selText = $(this).text();
                $(this).parents('.btn-group').find('.dropdown-toggle').html(selText + ' <span class="caret"></span>');
            });


            var facetview_howmany = $("#facetview_howmany").text();
            facetview_howmany = facetview_howmany.replace(/{{HOW_MANY}}/gi, options.paging.size);
            $("#facetview_howmany").text(facetview_howmany);
            //$(obj).append(thefacetview);
            // setup search option triggers
            $('#facetview_partial_match').bind('click', fixmatch);
            $('#facetview_exact_match').bind('click', fixmatch);
            $('#facetview_fuzzy_match').bind('click', fixmatch);
            $('#facetview_match_any').bind('click', fixmatch);
            $('#facetview_match_all').bind('click', fixmatch);
            $('#facetview_howmany').bind('click', howmany);

//            var url_options = $.getUrlVars();
//            // update the options with the latest q value
//            options.q = url_options.q;
//            $('#example-single').val(url_options.mode);
//            $('#example-single').multiselect({
//                onChange: function (element, checked) {
//                    options.brands = $('#example-single option:selected');
//                    
//                    //window.location.href = window.location.href.replace(/[\?#].*|$/, "?mode=" + brands.val());
//                }
//            });

            if (options.use_delay)
                whenready();

        });

    };

    // facetview options are declared as a function so that they can be retrieved
    // externally (which allows for saving them remotely etc.)
    $.fn.facetview.options = {};

})(jQuery);


