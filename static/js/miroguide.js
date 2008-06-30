/* channelguide.js
 * 
 * Shared functions used in channel guide
 */

function isMiro() {
    return (navigator.userAgent.indexOf('Miro') != -1 ||
	    (top.frames.length == 2 &&
	     top.frames[1].name == 'miro_guide_frame'));
}

function MiroVersion() {
    if (navigator.userAgent.indexOf('Miro') != -1) {
	return /Miro\/([\d.]+)/.exec(navigator.userAgent)[1];
    } else if (top.frames.length == 2 &&
	       top.frames[1].name == 'miro_guide_frame') {
	return "1.2";
    } else {
	return undefined;
    }
}

function showLoadIndicator(always) {
    if (always || navigator.userAgent.indexOf('Miro') != -1) {
	indicator = $("#load-indicator");
	indicator.animate({bottom: 0}, 'fast');
    }
}

function hideLoadIndicator() {
    indicator = $("#load-indicator").css('bottom', '-30px');
}

function makeXMLHttpRequest() {
    if (window.XMLHttpRequest) { // Mozilla, Safari, ...
        return new XMLHttpRequest();
    } else if (window.ActiveXObject) { // IE
        try {
            return new ActiveXObject("Msxml2.XMLHTTP");
        } catch (e) {}
        try {
            return new ActiveXObject("Microsoft.XMLHTTP");
        } catch (e) {}
    }
    return null;
}

function doAjaxCall(url, callback) {
    var request = makeXMLHttpRequest();
    if (!request) return false;
    request.onreadystatechange = function() {
         if (request.readyState == 4) {
            if (request.status == 200) {
                callback(request);
            }
         }
    }; 
    request.open('GET', url, true);
    request.send(null);
    return true;
}

function ajaxLink(url, id) {
    var elt = document.getElementById(id);
    if (!elt) return true;
    function callback(request) {
        elt.innerHTML = request.responseText;
    }
    if (!doAjaxCall(url, callback)) return true;
    return false;
}

/* Handle a subscription link.  We need to hit the channelguide URL, then make
 * the browser navigate to the subscribe link.  This is basically a hack
 * because some older version of democracy get confused because the
 * channelguide URL redirects te the subscribe_url.
 */
function handleSubscriptionLink(channel_guide_url, subscribe_url) {
    if (isMiro() && MiroVersion() >= "1.5") return true;
    request = makeXMLHttpRequest();
    if (!request) return true;
    request.onreadystatechange = function() {
        if (request.readyState == 2) {
            window.location.href = subscribe_url;
        }
    };
    request.open('GET', channel_guide_url, true);
    request.send(null);
    return false;
}

function handleFormLink(url) {
    showLoadIndicator();
    window.location.href = url;
    return false;
}

function searchFocus() {
    input = $(this);
    if (input.hasClass('headSearch'))
        input.removeClass('headSearch').val('');
}

function searchBlur() {
    input = $(this);
    if (!input.val()) {
        input.addClass('headSearch').val('Search');
    }
}

$(document).ajaxStart(function() {
    showLoadIndicator(true);
}).ajaxStop(function() {
    hideLoadIndicator();
});

if (isMiro()) {
    document.write('<style type="text/css">.only-in-miro {  display: inherit !important;}.only-in-browser {  display: none !important;}</style>');
}