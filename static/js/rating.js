/**
 * Star Rating - jQuery plugin
 *
 * Copyright (c) 2007 Wil Stuckey
 * Modified by John Resig and Paul Swartz
 *
 * Dual licensed under the MIT and GPL licenses:
 *   http://www.opensource.org/licenses/mit-license.php
 *   http://www.gnu.org/licenses/gpl.html
 *
 */

/**
 * Create a degradeable star rating interface out of a simple form structure.
 * Returns a modified jQuery object containing the new interface.
 *   
 * @example jQuery('form.rating').rating();
 * @cat plugin
 * @type jQuery 
 *
 */
jQuery.fn.rating = function(){
    return this.each(function(){
        var ratingValue;
        var ul = jQuery(this);
        if (ul.attr('user')) {
            ratingValue = parseFloat(ul.attr('user'));
        } else {
            ratingValue = parseFloat(ul.attr('average'));
        }

        var ratingType = (ul.find('li').hasClass('userrating') ?
                          'userrating' : 'averagerating');
        var ratingIndex = parseInt(ratingValue);
        var ratingPercent = (parseFloat(ratingValue) - ratingIndex) * 10;

        // hover events and focus events added
        var stars = ul.find("li.star")
            .mouseover(drainFill).focus(drainFill)
            .mouseout(drainReset).blur(drainReset)
            .click(click).each(setURL);

        // cancel button events
        var cancel = ul.find("li.cancel")
            .mouseover(drainAdd).focus(drainAdd)
            .mouseout(resetRemove).blur(resetRemove)
            .click(click).each(setURL);

        reset();

        function setURL(elem) {
            // this moves the link to the li, so that the crazy URL
            // doesn't show up in the status bar
            a = jQuery(this).find('a');
            a.parent().attr('href',a[0].href);
            a.removeAttr('href');
        }
        
        function drainFill(){ drain(); fill(this); }
        function drainReset(){ drain(); reset(); }
        function resetRemove(){ jQuery(this).removeClass('hover'); reset();}
        function drainAdd(){ drain(); jQuery(this).addClass('hover'); }

        function click(){
            ratingValue = ratingIndex = stars.index(this) + 1;
            ratingPercent = 0;
            ratingType = "userrating"
            url = jQuery(this).attr('href');
            var request = jQuery.get(url);
            stars.hide();
            cancel.hide()
            ul.find('.saving').show();
            request.onreadystatechange = function() {
                if (request.readyState == 4) {
                    ul.find('.saving').hide();
                    stars.show();
                    cancel.show();
                    if (request.responseText.indexOf('<div class="login-page">') != -1) {
                        // user isn't logged in, go go to the URL directly
                        // and it'll redirect to the login page
                        document.location = url;
                    }
                }
            };
            return false;
        }

        // fill to the current mouse position.
        function fill( elem ){
            stars.slice(0, stars.index(elem) + 1 ).addClass("hover");
        }
    
        // drain all the stars.
        function drain(){
            stars.removeClass("on hover");
            cancel.removeClass("on hover");
        }

        // Reset the stars to the default index.
        function reset(){
            stars.removeClass("userrating").removeClass("averagerating");
            stars.slice(0, ratingIndex).addClass("on");

            var percent = ratingPercent ? ratingPercent * 10 : 0;
            if (percent > 0)
                stars.slice(ratingIndex, ratingIndex+1).addClass("on").children("a").css("width", percent + "%");
            stars.addClass(ratingType)
            if (ratingType == 'userrating' && ratingValue=='0') {
                cancel.addClass('on');
            }
        }
    });
};

// fix ie6 background flicker problem.
if ( jQuery.browser.msie == true )
    document.execCommand('BackgroundImageCache', false, true);

$(document).ready(function () {
/*    try {*/
        $("ul.rating").rating();
/*    } catch (e) {}*/
});
