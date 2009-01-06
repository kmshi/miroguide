# Copyright (c) 2008 Participatory Culture Foundation
# See LICENSE for details.

import datetime
import urllib

import feedparser
from django.conf import settings
from django.http import Http404, HttpResponseRedirect, HttpResponse

from channelguide.guide.models import (Channel, Item)
from channelguide import util, cache


EMAIL_URL = "http://www.videobomb.com/index/democracyemail?url=%s"
VIDEOBOMB_URL = "http://www.videobomb.com/api/submit_or_bomb"
DELICIOUS_URL = "http://del.icio.us/post?v=4&noui&jump=close&url=%s&title=%s"
DIGG_URL = "http://digg.com/submit/?url=%s&media=video"
REDDIT_URL = "http://reddit.com/submit?url=%s&title=%s"
STUMBLEUPON_URL = "http://www.stumbleupon.com/submit?url=%s&title=%s"
FACEBOOK_URL = "http://www.facebook.com/share.php?u=%s"


class FakeItem(object):
    def __init__(self, name, url, description, date, thumbnail_url):
        self.name = name
        self.url = url
        self.description = description
        self.date = date
        self.thumbnail_url = thumbnail_url

        self.fake = True

    def thumb(self):
        url = self.thumb_url(98, 68)
        return util.mark_safe(
            '<img width="98" height="68" src="%s" alt="%s">' % (
                url, self.name.replace('"', "'")))

    def get_url(self):
        pass

class FakeChannel(object):
    def __init__(self, name, description, url, website_url, thumbnail_url):
        self.name = name
        self.description = description
        self.url = url
        self.website_url = website_url
        self.thumbnail_url = thumbnail_url

        # Things required by the template that should be left empty
        self.categories = []
        self.tags = []
        self.hi_def = False

        self.fake = True

    def get_subscribe_hit_url(self):
        return self.get_url() + '/subscribe-hit'

    def get_subscription_url(self):
        if self.url:
            return util.get_subscription_url(
                self.url, trackback=self.get_subscribe_hit_url())
        else:
            return util.get_subscription_url(
                self.website_url, type='site',
                trackback=self.get_subscribe_hit_url())

    def website_link(self):
        url_label = self.website_url
        url_label = util.chop_prefix(url_label, 'http://')
        url_label = util.chop_prefix(url_label, 'https://')
        url_label = util.chop_prefix(url_label, 'www.')
        return util.make_link(self.website_url, url_label)

    def thumb_url_245_164(self):
        # wrap in code that will constrain the width and height here
        pass


def get_feed_links(channel):
    share_email = EMAIL_URL % (
        urllib.quote(channel.url))
    share_delicious = DELICIOUS_URL % (
        urllib.quote(channel.url), urllib.quote(channel.name))
    share_digg = DIGG_URL % urllib.quote(channel.url)
    share_reddit = REDDIT_URL % (
        urllib.quote(channel.url), urllib.quote(channel.name))
    share_stumbleupon = STUMBLEUPON_URL % (
        urllib.quote(channel.url), urllib.quote(channel.name))
    share_facebook = FACEBOOK_URL % (
        urllib.quote(channel.url))

    ## Generate dictionary
    share_links = {
        'email': share_email,
        'delicious': share_delicious,
        'digg': share_digg,
        'reddit': share_reddit,
        'stumbleupon': share_stumbleupon,
        'facebook': share_facebook}

    return share_links


def share_feed(request):
    try:
        feed_url = str(request.GET['feed_url'])
    except:
        return HttpResponse("you must supply a feed_url")

    feed_key = 'share_feed-' + feed_url
    items_key = 'share_feed_items-' + feed_url

    # check the cache.  If not...
    cached_channel = cache.client.get(feed_key)
    cached_items = cache.client.get(items_key)
    if cached_channel:
        channel = cached_channel
        items = cached_items
    else:
        # check to see if we have that feed in our database...
        channels = Channel.query().where(url=feed_url).execute(request.connection)
        if channels:
            channel = channels[0]
            cache.client.set(feed_key, channel)

            item_query = Item.query(channel_id=channel.id).join('channel')
            item_query = item_query.order_by('date', desc=True).limit(4)
            items = item_query.execute(request.connection)
            cache.client.set(items_key, items)
        else:
            ## parse the feed
            parsed = feedparser.parse(feed_url)

            #ok, so this doesn't work...
            if hasattr(parsed, 'status') and parsed.status != 200:
                return HttpResponse("That feed appears to be dead.")

            ## generate fake channel
            if parsed.feed.has_key('thumbnail'):
                thumbnail_url = parsed.feed.thumbnail.href
            else:
                thumbnail_url = \
                    settings.STATIC_BASE_URL + 'images/generic_feed_thumb.png'
            
            channel = FakeChannel(
                parsed.feed.get('title'),
                parsed.feed.get('subtitle'),
                feed_url,
                parsed.feed.get('link'),
                thumbnail_url)

            items = []
            for entry in parsed.entries[:4]: # do we need to sort by date here?
                item = FakeItem(
                    entry.title,
                    entry.link,
                    entry.summary,
                    datetime.datetime(*entry.updated_parsed[:7]),
                    thumbnail_url) # just use whatever thumbnail the channel has?
                items.append(item)

            cache.client.set(feed_key, channel)
            cache.client.set(items_key, items)

    share_links = get_feed_links(channel)

    return util.render_to_response(
        request, 'show-channel.html',
        {'channel': channel,
         'items': items,
         'share_links': share_links})


def share_item(request):
    # check to see if we have that item in our database...
    # If so
    #   use that item
    # else
    #   let's create a "fake" item to preview
    # render that item preview
    pass
