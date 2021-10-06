// add extension to jQuery with a function to get URL parameters
jQuery.extend({
    getUrlVars: function () {
        var params = new Object;
        var hashes = window.location.href.slice(window.location.href.indexOf('?') + 1).split('&')
        for (var i = 0; i < hashes.length; i++) {
            hash = hashes[i].split('=');
            if (hash.length > 1) {
                if (hash[0] == "q")
                    params[hash[0]] = hash[1];
                else {
                    if (hash[1].replace(/%22/gi, "")[0] == "[" || hash[1].replace(/%22/gi, "")[0] == "{") {
                        hash[1] = hash[1].replace(/^%22/, "").replace(/%22$/, "");
                        var newval = JSON.parse(unescape(hash[1].replace(/%22/gi, '"')));
                    } else {
                        var newval = unescape(hash[1].replace(/%22/gi, ""));
                    }
                    params[hash[0]] = newval;
                }
               
            }
        }
        return params;
    },
    getUrlVar: function (name) {
        return jQuery.getUrlVars()[name];
    }
});

// first define the bind with delay function from (saves loading it separately) 
// https://github.com/bgrins/bindWithDelay/blob/master/bindWithDelay.js

(function ($) {
    $.fn.bindWithDelay = function (type, data, fn, timeout, throttle) {
        var wait = null;
        var that = this;

        if ($.isFunction(data)) {
            throttle = timeout;
            timeout = fn;
            fn = data;
            data = undefined;
        }

        function cb() {
            var e = $.extend(true, {}, arguments[0]);
            var throttler = function () {
                wait = null;
                fn.apply(that, [e]);
            };

            if (!throttle) {
                clearTimeout(wait);
            }
            if (!throttle || !wait) {
                wait = setTimeout(throttler, timeout);
            }
        }

        return this.bind(type, data, cb);
    };

    //adjust popver placement depending on the position to avoid overflows
    $.fn.placement = function (context, source) {
        var position = $(source).position();

        if (position.left > 300) {
            return "left";
        }

        if (position.left < 515) {
            return "right";
        }

        if (position.top < 110) {
            return "bottom";
        }

        return "top";
    }
})(jQuery);

