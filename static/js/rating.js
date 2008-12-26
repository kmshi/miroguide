/*
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

/*
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
        var div;
        if (this.tagName == "FORM") {
            div = jQuery("<div/>").attr({
                title: this.title,
                className: this.className
            });
            var names = star_names;

            jQuery(this).find("select option").each(function(){
                div.append( this.value == "0" ?
                            "<div class='cancel'><a href='#0' title='" + names[this.value] + "'></a></div>" :
                            "<div class='star'><a href='#" + this.value + "' title='" + names[this.value] + "'>" + this.value + "</a></div>" );
            });
        } else {
            div = jQuery(this);
        }

        var ratingType;
        if (this.title.split(/ /)[0] == "User") {
            ratingType = "userrating";
        } else {
            ratingType = "averagerating";
        }
        var ratingValue = this.title.split(/:\s*/)[1],
            url = this.action,
            ratingIndex = parseInt(ratingValue);
        var ratingPercent = (parseFloat(ratingValue) - ratingIndex) * 10;

        // hover events and focus events added
        var stars = div.find("div.star")
            .mouseover(drainFill).focus(drainFill)
            .mouseout(drainReset).blur(drainReset)
            .click(click);

        // cancel button events
        var cancel = div.find("div.cancel")
            .mouseover(drainAdd).focus(drainAdd)
            .mouseout(resetRemove).blur(resetRemove)
            .click(click);

        drainReset();

        if (this.tagName == "FORM")
            div.insertAfter(this);

        function drainFill(){ drain(); fill(this); }
        function drainReset(){ drain(); reset(); }
        function resetRemove(){ jQuery(this).removeClass('on'); reset();}
        function drainAdd(){ drain(); jQuery(this).addClass('on'); }

        function click(){
            ratingValue = ratingIndex = stars.index(this) + 1;
            ratingPercent = 0;
            ratingType = "userrating"
            var request = jQuery.get(url,{
                rating: jQuery(this).find('a')[0].href.slice(-1)
            });
            request.onreadystatechange = function() {
                if (request.readyState == 4 && request.status == 302)
                    document.location = request.getResponseHeader('Location');
                if (request.readyState == 4 && request.status == 200) {
                    if (request.responseText.indexOf('<div class="login-page">') != -1) {
                        document.location = url+'?rating=' + ratingValue;
                    }
                }
            };
            return false;
        }

        // fill to the current mouse position.
        function fill( elem ){
            stars.find("a").css("width", "100%");
            stars.slice(0, stars.index(elem) + 1 ).addClass("hover");
        }
    
        // drain all the stars.
        function drain(){
            stars.removeClass("on hover").children('a').css('width', '');
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
    }).filter('form').remove();
};

// fix ie6 background flicker problem.
if ( jQuery.browser.msie == true )
    document.execCommand('BackgroundImageCache', false, true);

$(document).ready(function () {
    try {
        $("form.rating").rating('', {maxvalue:5});
    } catch (e) {}
    $('.rating').each(function() {
        var height = 25;
        // if ($(this).hasClass('small')) {
        //     height = 13;
        // }
        $(this).height(height);
    })
});
