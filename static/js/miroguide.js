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
    indicator = $("#load-indicator");
    if ((!indicator.queue().length) && always || navigator.userAgent.indexOf('Miro') != -1) {
	indicator.animate({bottom: 0}, 'fast');
    }
}

function hideLoadIndicator() {
    indicator = $("#load-indicator").stop().css('bottom', '-30px');
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
    request.subscribe_url = subscribe_url;
    request.onreadystatechange = function () {
        if (request.readyState == 2)
            _redirectToSubscription(request);
    }
    request.open('GET', channel_guide_url, true);
    request.send(null);
    return false;
}

function _redirectToSubscription(request) {
    window.location.href = request.subscribe_url;
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

function searchPageShow(e) {
    $("#searchSpot input").val('Search');
}

function showHelpText(help, event) {
    name = $.trim(help.parent().parent().children('label').text());
    text = help.next().text();
    closeImg = help.attr('src').replace('ico_question', 'ico_close2');
    $(".help_box").remove();
    display = $("<div class='help_box'><div class='help_box_top'><a href='#' class='close'><img src='" + closeImg + "' alt='Close'></a><span>" + name + "</span></div><div class='help_box_inner'><p>" + text + "</p></div><div class='help_box_bottom'></div></div>");
    display.css('position', 'absolute').css('top',
                                            event.clientY - 31).css('left',
                                                               event.clientX);
    display.find('.close').click(function() {
        display.remove();
    });
    $("body").append(display);
}

function submitAChannel(submitLink) {
    url = submitLink.attr('href');
    hoverMenuSubmit = $('<div id="hoverMenuSubmit"></div>');
    $("#hover_align").append(hoverMenuSubmit);
    hoverMenuSubmit.load(url + ' #submit > *',
                         function() {
                             $('#hoverMenuLogin').hide();
                             $('#hoverMenuSubmit form').ajaxForm(
                                 showNewSubmitForm);});
}

function showNewSubmitForm(data, textStatus) {
    submit = $('div.top, form[method=post]', data);
    if (submit.length < 2)
        return $('body').empty().append(data);
    submit.find('h2').remove();
    submit.eq(1).ajaxForm(showNewSubmitForm);
    $('#hoverMenuSubmit').empty().append(submit);
}

$(document).ajaxStart(function() {
    showLoadIndicator(true);
}).ajaxStop(function() {
    hideLoadIndicator();
});

if (isMiro()) {
    document.write('<style type="text/css">.only-in-miro {  display: inherit !important;}.only-in-browser {  display: none !important;}</style>');
}