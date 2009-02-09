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
    if (!indicator.length)
        return;
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
}

function channelAdd(url, redirect, name, event) {
    var xhr = makeXMLHttpRequest();
    if (!xhr) return true;
    xhr.onreadystatechange = function() {
        if (xhr.readyState > 1) {
            display = $("<div class='added_channel'>" + name + " added to your Miro sidebar!</div>");
            display.css('position', 'absolute').css('top', event.pageY - 31).css('left', '-10em');
            $("body").append(display);
            display.animate({left: 0}, 'slow');
            setTimeout(function() {
                d = $('div.added_channel:eq(0)');
                d.animate({
                    left: '-20em'
                }, 'slow',  function() {
                    d.remove();
                });
            }, 2000);
            window.location = redirect;
        }
    };
    xhr.open('GET', url, true);
    xhr.send(null);
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
    searchInput = $(this);
    if (searchInput.hasClass('headSearch'))
        searchInput.removeClass('headSearch').val('');
}

function searchBlur() {
    searchInput = $(this);
    if (!searchInput.val()) {
        searchInput.addClass('headSearch').val('Search');
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
                                            event.pageY - 31).css('left',
                                                                  event.pageX);
    display.find('.close').click(function() {
        display.remove();
        return false;
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

function inBounds(val, min, length) {
    return (min < val && val < (min + length));
}

function isWithin(event, obj)  {
    return (inBounds(event.clientX, obj.offsetLeft, obj.offsetWidth) &&
            inBounds(event.clientY, obj.offsetTop, obj.offsetHeight))
}

function showMenu(el, menu, event) {
    $('#' + menu + ' a').addClass('hover');
    m = $('#' + menu)[0];
    $('#' + el).css('top', m.clientHeight + 34).show();
    return false;
}

function hideMenu(el, menu, event) {
    el_o = $('#' + el);
    menu_o = $('#' + menu);
    if (event) {
        if (isWithin(event, el_o[0]) || isWithin(event, menu_o[0])) {
            return;
        }

    }
    $('#' + el).hide();
    $('#' + menu + ' a').removeClass('hover');
    return false;
}

function showNewSubmitForm(data, textStatus) {
    /* form_data here refers to the new html code that we should *
       insert into the hovering box */
    form_data = $('div.top, form[method=post]', data)
    if (data == "SUBMIT SUCCESS") {
        /* this is basically a redirect */
        window.location.href = '/submit/after';
        return false;
    }
    /* form_data.find('h2').remove(); */
    $('#hoverMenuSubmit').empty().append(form_data);
    $('#hoverMenuSubmit form').ajaxForm(showNewSubmitForm);
}

var languageTimeout = null;

function languageUp() {
    showMenu('hoverMenuLanguage', 'language');
    ul = $("#hoverMenuLanguage ul:last");
    ul.scrollTop(ul.scrollTop() - 30);
    languageStop();
    languageTimeout = setTimeout(languageUp, 50);
}

function languageDown() {
    showMenu('hoverMenuLanguage', 'language');
    ul = $("#hoverMenuLanguage ul:last");
    ul.scrollTop(ul.scrollTop() + 30);
    languageStop();
    languageTimeout = setTimeout(languageDown, 50);
}

function languageStop() {
    if (!languageTimeout)
        return;
    clearTimeout(languageTimeout);
    languageTimeout = null;
}
function languageUpdate() {
    return;
    li = $("#hoverMenuLanguage ul:last li");
    top = parseInt(li.css('top'));
    count = li.length;
    up = $("#hoverMenuLanguage #upButton");
    down = $("#hoverMenuLanguage #downButton");
    if (top < 0) {
        up.css('cursor', 'pointer');
    } else {
        up.css('cursor', 'inherit');
    }
    if (count * -30 + 300 < top) {
        down.css('cursor', 'pointer');
    } else {
        down.css('cursor', 'inherit');
    }
}

function add_corners() {
    if (window.navigator.userAgent.indexOf('MSIE') == -1) {
        $('.corners').corners();
        $('.top_corners').corners('top');
    }
}

function setup_login_form() {
    $("#hoverMenuLogin form").ajaxForm(
        function(data, textStatus) {
            result = $('.form-errors ul li', data).addClass('form-errors');
            if (!result.length) {
                location.href = location.href;
                return;
            } else {
                $('#hoverMenuLogin .form-errors').replaceWith(result);
                $('#hoverMenuLogin .form-errors').show();
            }
        });
    $('#hoverMenuLogin:not(.loggedin) #register').click(
        function() {
            $('#hoverMenuLogin #login').hide();
            $('#hoverMenuLogin #registerHidden').show();
            return false;
        });
}

$(document).ajaxStart(function() {
    showLoadIndicator(true);
}).ajaxStop(function() {
    hideLoadIndicator();
});

if (isMiro()) {
    document.write('<style type="text/css">.only-in-miro {  display: inherit !important;}.only-in-browser {  display: none !important;}</style>');
}

if (window.addEventListener) {
    window.addEventListener('pageshow', searchPageShow, false);
    window.addEventListener('pagehide', hideLoadIndicator, false);
}
