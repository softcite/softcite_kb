var getEditFilterModal = function (which) {
    var editFilterModal = 
            '<div id="facetview_editmodal" class="modal">\
        <div class="modal-dialog">\
            <div class="modal-content">\
                <div class="modal-header"> \
                <a class="facetview_removeedit close">×</a> \
                <h3>Edit the facet parameters</h3> \
                </div> \
                <div class="modal-body"> \
				<form class="well">';
    for (truc in options.aggs[which]) {
        if (truc == 'type') {
            editFilterModal += '<div class="control-group"> \
					            <label class="control-label" for="select"><b>type</b></label> \
					            <div class="controls"> \
					              <select id="input_type"> \
					                <option';
            if (options.aggs[which]['type'] == 'date') {
                editFilterModal += ' selected ';
            }
            editFilterModal += '>date</option> \
					                <option';
            if (options.aggs[which]['type'] == 'class') {
                editFilterModal += ' selected ';
            }
            editFilterModal += '>class</option> \
					                <option';
            if (options.aggs[which]['type'] == 'entity') {
                editFilterModal += ' selected ';
            }
            editFilterModal += '>entity</option> \
					                <option';
            if (options.aggs[which]['type'] == 'taxonomy') {
                editFilterModal += ' selected ';
            }
            editFilterModal += '>taxonomy</option> \
					                <option';
            if (options.aggs[which]['type'] == 'cloud') {
                editFilterModal += ' selected ';
            }
            editFilterModal += '>cloud</option> \
                                    <option';
            if (options.aggs[which]['type'] == 'country') {
                editFilterModal += ' selected ';
            }
            editFilterModal += '>country</option> \
					              </select> \
					            </div> \
					          </div>';
        }
        else if (truc == 'view') {
            editFilterModal += '<div class="control-group"> \
					            <label class="control-label" for="select"><b>view</b></label> \
					            <div class="controls"> \
					              <select id="input_type"> \
					                <option';
            if (options.aggs[which]['view'] == 'hidden') {
                editFilterModal += ' selected ';
            }
            editFilterModal += '>hidden</option> \
					                <option';
            if (options.aggs[which]['view'] == 'graphic') {
                editFilterModal += ' selected ';
            }
            editFilterModal += '>graphic</option> \
					                <option';
            if (options.aggs[which]['view'] == 'textual') {
                editFilterModal += ' selected ';
            }
            editFilterModal += '>textual</option> \
					                <option';
            if (options.aggs[which]['view'] == 'all') {
                editFilterModal += ' selected ';
            }
            editFilterModal += '>all</option> \
					              </select> \
					            </div> \
					          </div>';
        }
        else {
            editFilterModal += '<div class="form-group"> \
						<label class="control-label" for="input"><b>' + truc + '</b></label> \
				 		<div class="controls"> \
						<input type="text" class="form-control" id="input_' + truc + '" value="'
                    + options.aggs[which][truc] + '"/> \
						</div></div>';
        }
    }

    editFilterModal += '</form> \
			    </div> \
                <div class="modal-footer"> \
                <a id="facetview_dofacetedit" href="#" class="btn btn-primary btn-danger" rel="' + which + '">Apply</a> \
                <a class="facetview_removeedit btn close">Cancel</a> \
                </div> \
                </div> \
</div> \
                </div>';

    return editFilterModal;


};

var facetrangeModal = '<div id="facetview_rangemodal" class="modal">\
        <div class="modal-dialog">\
            <div class="modal-content">\
                            <div class="modal-header"> \
                                <a class="facetview_removerange close">×</a> \
                                <h3>Set a filter range</h3> \
                            </div> \
                            <div class="modal-body"> \
                                <div style=" margin:20px;" id="facetview_slider"></div> \
                                <h3 id="facetview_rangechoices" style="text-align:center; margin:10px;"> \
                                <span class="facetview_lowrangeval">...</span> \
                                <small>to</small> \
                                <span class="facetview_highrangeval">...</span></h3> \
                            </div> \
                            <div class="modal-footer"> \
                                <a id="facetview_dofacetrange" href="#" class="btn btn-primary">Apply</a> \
                                <a class="facetview_removerange btn close">Cancel</a> \
                            </div> \
                            </div> \
                            </div> \
                </div>';
