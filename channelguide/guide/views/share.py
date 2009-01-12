# Copyright (c) 2008 Participatory Culture Foundation
# See LICENSE for details.

import datetime
import mimetypes
import urllib
import urlparse

import feedparser
from django.conf import settings
from django.http import Http404, HttpResponseRedirect, HttpResponse

from channelguide.guide.models import (Channel, Item)
from channelguide.guide.views import playback
from channelguide import util, cache


DELICIOUS_URL = "http://del.icio.us/post?v=4&noui&jump=close&url=%s&title=%s"
DIGG_URL = "http://digg.com/submit/?url=%s&media=video"
REDDIT_URL = "http://reddit.com/submit?url=%s&title=%s"
STUMBLEUPON_URL = "http://www.stumbleupon.com/submit?url=%s&title=%s"
FACEBOOK_URL = "http://www.facebook.com/share.php?u=%s"


# Custom exceptions for this module
class Error(Exception): pass
class FeedFetchingError(Error): pass


class FakeItem(object):
    def __init__(self, url, name=None, description=None,
                 date=None, thumbnail_url=None):
        self.url = url
        self.name = name
        self.description = description
        self.date = date
        self.thumbnail_url = thumbnail_url

        self.fake = True

        self.mime_type = mimetypes.guess_type(self.url)

    def thumb(self):
        return util.mark_safe(
            '<img width="98" height="68" src="%s" alt="%s">' % (
                self.thumbnail_url, self.name.replace('"', "'")))

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
        return self.thumbnail_url


def get_share_links(url, name):
    share_delicious = DELICIOUS_URL % (
        urllib.quote(url), urllib.quote(name))
    share_digg = DIGG_URL % urllib.quote(url)
    share_reddit = REDDIT_URL % (
        urllib.quote(url), urllib.quote(name))
    share_stumbleupon = STUMBLEUPON_URL % (
        urllib.quote(url), urllib.quote(name))
    share_facebook = FACEBOOK_URL % (
        urllib.quote(url))

    ## Generate dictionary
    share_links = {
        'delicious': share_delicious,
        'digg': share_digg,
        'reddit': share_reddit,
        'stumbleupon': share_stumbleupon,
        'facebook': share_facebook}

    return share_links


def get_channels_and_items(feed_url, connection):
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
        channels = Channel.query().where(url=feed_url).execute(connection)
        if channels:
            channel = channels[0]
            cache.client.set(feed_key, channel)

            item_query = Item.query(channel_id=channel.id).join('channel')
            item_query = item_query.order_by('date', desc=True).limit(4)
            items = item_query.execute(connection)
            cache.client.set(items_key, items)
        else:
            ## parse the feed
            parsed = feedparser.parse(feed_url)

            #ok, so this doesn't work...
            if hasattr(parsed, 'status') and parsed.status != 200:
                raise FeedFetchingError("Got a non-200 status while parsing feed")

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
            # why not limit the number of items here to 4?
            # Because we might need to check to see if a particular
            # item is in this feed if it's being faked...
            for entry in parsed.entries:
                item = FakeItem(
                    entry.link,
                    entry.title,
                    entry.summary,
                    datetime.datetime(*entry.updated_parsed[:7]),
                    thumbnail_url) # just use whatever thumbnail the channel has?
                items.append(item)

            cache.client.set(feed_key, channel)
            cache.client.set(items_key, items)

    return channel, items

def share_feed(request):
    try:
        feed_url = str(request.GET['feed_url'])
    except KeyError:
        return HttpResponse("you must supply a feed_url")

    try:
        channel, items = get_channels_and_items(feed_url, request.connection)
    except FeedFetchingError:
        return HttpResponse("This feed appears to be dead.")

    share_links = get_share_links(channel.url, channel.name)

    return util.render_to_response(
        request, 'show-channel.html',
        {'channel': channel,
         'items': items[:4],
         'share_links': share_links})


def share_item(request):
    # check to see if we have that item in our database...
    # If so
    #   use that item
    # else
    #   let's create a "fake" item to preview
    # render that item preview
    try:
        file_url = str(request.GET['file_url'])
    except KeyError:
        return HttpResponse("you must supply a file_url")

    feed_url = request.GET.get('feed_url')
    webpage_url = request.GET.get('webpage_url')
    item_name = request.GET.get('item_name')

    item = None
    next = None
    previous = None

    if webpage_url:
        webpage_url = str(webpage_url)

    if feed_url:
        feed_url = str(feed_url)
        try:
            channel, channel_items = get_channels_and_items(
                feed_url, request.connection)
        except FeedFetchingError:
            return HttpResponse("This feed appears to be dead.")

        # see if we have that item in the feed
        ## if it's a fake feed check the full list of items
        if isinstance(channel, FakeChannel):
            i = 0
            for this_item in channel_items:
                if this_item.url == file_url:
                    item = this_item
                    break
                i += 1
            if item:
                if i != 0:
                    previous = channel_items[i - 1]
                if len(channel_items) != i + 1:
                    next = channel_items[i + 1]

        ## if it's a real feed do a query
        else:
            # do a query for this item
            item_query = Item.query(channel_id=channel.id, url=file_url)
            item_query = item_query.join('channel')
            item_query = item_query.order_by('date', desc=True).limit(1)
            items = item_query.execute(request.connection)
            if items:
                item = items[0]

                ## check for previous
                previous_set = Item.query(
                    Item.c.channel_id == item.channel_id,
                    Item.c.date < item.date)
                previous_set = previous_set.limit(1)
                previous_set = previous_set.order_by(Item.c.date, desc=True)
                previous_set = previous_set.execute(request.connection)
                if previous_set:
                    previous = previous_set[0]
                
                ## check for next
                next_set = Item.query(
                    Item.c.channel_id == item.channel_id,
                    Item.c.date > item.date)
                next_set = next_set.limit(1).order_by(Item.c.date)
                next_set = next_set.execute(request.connection)
                if next_set:
                    next = next_set[0]

    ## if we don't have an item at this point, we need to generate
    ## a fake one.  It won't have much useful info though...
    if not item:
        if not item_name:
            subpath = urlparse.urlsplit(file_url)[3]
            if subpath:
                item_name = subpath.split('/')[-1]

            else:
                item_name = file_url

        item = FakeItem(file_url, item_name)

    # get the sharing info
    share_links = get_share_links(item.url, item.name)

    # render the page
    return util.render_to_response(
        request, 'playback.html',
        {'item': item,
         'channel': channel,
         'previous': previous,
         'next': next,
         'embed': util.mark_safe(playback.embed_code(item))})
