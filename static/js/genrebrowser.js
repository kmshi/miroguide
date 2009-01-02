var browser = {
    scrollTimeout: null,

    browseGenre: function(obj) {
        previousName = $(obj).parent().parent().find('a.selected').removeClass('selected').text();
        genreName = $(obj).addClass('selected').text();
        viewAll = $('#channelEpisodes a.view_all_videos');
        viewAll.attr('href', viewAll.attr('href').replace(escape(previousName),  escape(genreName))).children('strong').text(genreName);
        browser.loadMostPopular(genreName);
        browser.loadNewest(genreName);
        return false;
    },

    loadMostPopular: function(genreName) {
        browser.getChannels(genreName, '-popular', 'browser.cb_loadMostPopular');
    },

    loadNewest: function(genreName) {
        browser.getChannels(genreName, '-age', 'browser.cb_loadNewest');
    },

    getChannels: function(genreName, sort, callback) {
        url = '/api/get_channels?datatype=json&jsoncallback=' + escape(callback) +
            '&sort=' + sort + '&limit=2&filter=category&filter_value=' + escape(genreName);
        $.getScript(url);
    },

    cb_loadMostPopular: function(channels) {
        browser.updateChannel(0, channels[0]);
        browser.updateChannel(1, channels[1]);
        add_corners();
    },

    cb_loadNewest: function(channels) {
        browser.updateChannel(2, channels[0]);
        browser.updateChannel(3, channels[1]);
        add_corners();
    },

    updateChannel: function(index, data) {
        item = $("#channelEpisodes .pageContent .searchResults > li").eq(index);
        thumb = item.find('.searchThumb a');
        url = '/feeds/' + data['id'];
        STATIC_BASE_URL = /(.*)media\/thumbnails\//.exec(data['thumbnail_url'])[1];
        thumb_url = data['thumbnail_url'].replace('370x247', '98x68');
        thumb.attr('href', url);
        thumb.children('div').css('background-image', 'url(' + thumb_url + ')').children('img.hd_tag_tiny2').remove();
        if (data['hi_def']) {
            thumb.children('div').html('<img class="hd_tag_tiny2" src="' + STATIC_BASE_URL + 'images/ico_hd_tag_tiny.png" alt="" />');
        }
        title = item.find('h4 a');
        title.attr('href', url).text(data['name']);
        description = item.find('.searchResultContent p');
        description.text(data['description']);
        add = item.find('a.add_feed_button2').attr('href', url);

        $.getJSON('/api/get_channel?id=' + data['id'] + '&datatype=json&jsoncallback=?',
                   function(data) {
                       item = $("#channelEpisodes .pageContent .searchResults > li").eq(index);
                       item.find('li.subscribers').text(data['subscription_count_today'] + ' Subscribed Today');
                       if (data['score']) {
                           item.find('div.rating').attr('title', 'User Rating: ' + data['score']).rating();
                       } else {
                           item.find('div.rating').attr('title', 'Average Rating: ' + data['average_rating']).rating();
                       }
                   });
    },

    scrollStop: function() {
        if (!browser.scrollTimeout)
            return;
        clearTimeout(browser.scrollTimeout);
        browser.scrollTimeout = null;
    },

    scrollUp: function() {
        div = $("#channelEpisodes ul.scrollNav div");
        top = parseInt(div.attr('scrollTop'));
        div.attr('scrollTop', top - 24);
        browser.scrollStop();
        browser.scrollTimeout = setTimeout(browser.scrollUp, 50)
    },

    scrollDown: function() {
        div = $("#channelEpisodes ul.scrollNav div");
        top = parseInt(div.attr('scrollTop'));
        div.attr('scrollTop', top + 24);
        browser.scrollStop();
        browser.scrollTimeout = setTimeout(browser.scrollDown, 50)
    }
}