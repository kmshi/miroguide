hover = {

    cachedData: {},
    loading: false,

    load: function(showIDs) {
        hover.loading = true;
        if (showIDs === undefined) {
            showIDs = $.map($('.show_hover'), function(elem, index) {
                showID = (/hover_(\d+)/).exec(elem.className)[1];
                if (hover.cachedData[showID] === undefined) {
                    return showID;
                } else {
                    return null;
                }
            });
        }
        url = '/api/get_channel?datatype=json&';
        for (i=0; i < showIDs.length; i ++) {
            if (hover.cachedData[showIDs[i]]) {
                continue;
            }
            if (showIDs[i] !== undefined) {
                url += 'id=' + showIDs[i] + '&';
            }
        }
        url += 'jsoncallback=?';
        $.getJSON(url, function(data) {
            hover.loading = false;
            for (i=0; i < data.length; i ++) {
                hover.cachedData[data[i].id] = data[i];
            }
        });
        hideLoadIndicator();
    },

    show: function (event) {
        hoverDiv = $(this);
        showID = /hover_(\d+)/.exec(this.className)[1];
        $('.show_hover + .know_more').filter(
            function() {
                return hoverDiv.parent().children('.hover_' + showID).length;
            }).hide();
        $('.show_hover + .know_more').not('.hover_' + showID + ' + .know_more').hide();
        existingDiv = hoverDiv.parent().find('.know_more');
        if (existingDiv.find('.inner').length) {
            if (existingDiv.find('.inner').children().length) {
                existingDiv.show();
                return;
            }
        } else {
            div = $('<div/>').attr('class', 'know_more').attr('id', 'know_more_' + showID);
            div.append($("<div/>").addClass('bottom')).children().append(
                $("<div/>").addClass('extra_for_left')).children().append(
                    $("<div/>").addClass('arrow')).children().append(
                        $("<div/>").addClass('inner'));
            if (event.pageX > $(window).width() / 2) {
                div.addClass('dir_right');
            } else {
                div.addClass('dir_left');
            }
            div.hide().css('display', 'none');
            hoverDiv.after(div);
        }
        if (hover.cachedData[showID]) {
            hover.JSONcallback(hoverDiv, hover.cachedData[showID]);
            return;
        }

        url = '/api/get_channel?datatype=json&id=' + showID;
        $.getJSON(url, function(data) {
            hover.cachedData[data.id] = data;
            hover.JSONcallback(hoverDiv, data);
        });
    },

    stripTags: function (text) {
        return text.replace(/<[^>]+>/g, '');
    },

    JSONcallback: function (hoverDiv, show) {
        div = hoverDiv.parent().find('.know_more').eq(0);
        if (div.length === 0) {
            return;
        }
        html = '<div class="actions">';
        // add to sidebar button
        html += '<a href="' + show.subscribe_url.replace('&', '&amp;') + "\" onclick=\"return handleSubscriptionLink('" + show.subscribe_hit_url.replace('&', '&amp;') + "', '" + show.subscribe_url.replace('&', '&amp;') + "');\" class=\"small_add_button feed\"> ";
        html += '<span>' + gettext('Add to Sidebar') + '</span> ';
        html += '</a>';
        if (show.item.length) {
            // preview button
            html += '<a href="' + show.item[0].playback_url + '" class="preview"><span>';
            if (show.details_url.indexOf('audio') != -1) {
                html += gettext('Listen');
            } else {
                html += gettext('Watch');
            }
            html += '</span></a>';
        }
        html += '</div>';
        html += '<div class="rate">';
        // details button
        html += '<a href="'+ show.details_url + '" class="rollover_button"><span>' + gettext('More Details') + '</span></a>';
        html += '<div class="stars"><form class="rating" method="GET" title="';
        if (show.score === undefined || show.score === null) {
            html += 'Average Rating:' + show.average_rating;
        } else {
            html += 'User Rating: ' + show.score;
        }
        html += '" action="/channels/' + show.id + ' /rate/"><div><input type="hidden" name="referer" value="/feeds/' + show.id + '"> <label for="rating_channel_' + show.id + '" class="avg">Rate Me!</label> <select name="rating" id="rating_channel_' + show.id + '"><option value="0">0</option><option value="1">1</option><option value="2">2</option><option value="3">3</option><option value="4">4</option><option value="5">5</option></select><input type="submit" value="Go"></div></form></div>';
        if (show.count_rating) {
            html += '<div class="count">' + interpolate(ngettext("Avg. of %s Rating:", 'Avg. of %s Ratings:', show.count_rating), [show.count_rating]) + ' ' + interpolate(ngettext("1 Star", "%s Stars", show.average_rating), [show.average_rating]) + '</div>';
        }
        html += '</div><!-- end rate -->';
        html += '<h4>' + show.name + '</h4><div class="desc">';
        showDescription = hover.stripTags(show.description);

        if (showDescription.length > 285) {
            lastSpace = showDescription.indexOf(' ', 285);
            showDescription = showDescription.slice(0, lastSpace) + '...';
        }
        html += '<p>' + showDescription +'</p></div><div class="tags">';
        if (show.category.length) {
            html += '<p><strong>' + gettext("Genres") + '</strong> - ';
            for (i=0; i < show.category.length; i++) {
                cat = show.category[i];
                html += '<a href="/genres/' + cat + '" onclick="showLoadIndicator();">' + cat + '</a>';
                if (i < show.category.length - 1) {
                    html += ', ';
                }
            }
            html += '</p>';
        }
        if (show.tag.length) {
            html += '<p><strong>' + gettext("Tags") + '</strong> - ';
            for (i=0; i < show.tag.length && i < 5; i++) {
                tag = show.tag[i];
                html += '<a href="/tags/' + tag + '" onclick="showLoadIndicator();">' + tag + '</a>';
                if (i < show.tag.length - 1 && i < 4) {
                    html += ', ';
                }
            }
            html += '</p>';
        }
        html += '</div>';
        div.find('.inner').html(html);
        div.hover(hover.popupShow, hover.popupHide);
        div.find('form.rating').rating('', {maxvalue: 5});
        div.find('.rating').height(25);
        div.show();
    },

    hide: function(event) {
        node = event.relatedTarget;
        while (node) {
            if ($(node).hasClass('know_more')) {
                // moved into the popup
                return;
            }
            node = node.parentNode;
        }

        know_more = $(this).parent().children(".know_more");
        if (!know_more.hasClass('open')) {
            know_more.hide();
        }
        if (hover.loading) {
            know_more.remove();
        }
    },

    popupShow: function (event) {
        $(this).addClass('open').show();
        event.stopPropagation();
    },

    popupHide: function(event) {
        $(this).removeClass('open');
        if (!$(event.relatedTarget).hasClass('hover')){
            $(this).hide();
        }
        event.stopPropagation();
    }
};

$(document).ready(function () {
    $('.show_hover').hover(hover.show, hover.hide);
});