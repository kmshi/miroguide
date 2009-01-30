# Copyright (c) 2008 Participatory Culture Foundation
# See LICENSE for details.

import datetime
import urllib
import urlparse

import feedparser
from django.conf import settings
from django.http import HttpResponseRedirect, HttpResponse
from django.template import loader, Context
from django.utils.translation import gettext as _

from channelguide import util, cache
from channelguide.guide import filetypes
from channelguide.guide.forms.share import ShareForm
from channelguide.guide.models import (Channel, Item)
from channelguide.guide.views import playback


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

        self.mime_type = filetypes.guessMimeType(self.url)

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

            if parsed.bozo: # this didn't work either
                raise FeedFetchingError('Feed is unparsable')

            ## generate fake channel
            thumbnail_url = (
                settings.STATIC_BASE_URL + 'images/generic_feed_thumb.png')

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
                updated_datetime = None
                if entry.get('updated_parsed'):
                    updated_datetime = datetime.datetime(*entry.updated_parsed[:7])
                item = FakeItem(
                    entry.link,
                    entry.title,
                    entry.summary,
                    updated_datetime,
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

    if isinstance(channel, Channel):
        return HttpResponseRedirect('/feeds/%s?share=true' % channel.id)

    share_url = urlparse.urljoin(
        settings.BASE_URL_FULL,
        '/share/feed/?feed_url=%s&share=false' % urllib.quote(feed_url))

    share_links = None
    share_button_url = None
    if request.GET.get('share') == 'false':
        share_button_url = urlparse.urljoin(
            settings.BASE_URL_FULL,
            '/share/feed/?feed_url=%s' % urllib.quote(feed_url))
    else:
        share_links = util.get_share_links(share_url, channel.name)

    return util.render_to_response(
        request, 'show-channel.html',
        {'channel': channel,
         'items': items[:4],
         'feed_url': feed_url,
         'share_url': share_url,
         'share_button_url': share_button_url,
         'share_type': 'feed',
         'google_analytics_ua': None,
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
    else:
        channel = None

    if isinstance(item, Item):
        return HttpResponseRedirect('/items/%s?share=true' % item.id)

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
    get_params = {'file_url': file_url, 'share': 'false'}
    if feed_url:
        get_params['feed_url'] = feed_url
    if webpage_url:
        get_params['webpage_url'] = webpage_url
    if item_name:
        get_params['item_name'] = feed_url

    share_url = urlparse.urljoin(
        settings.BASE_URL_FULL,
        '/share/item/?%s' % urllib.urlencode(get_params))

    share_links = None
    share_button_url = None
    if request.GET.get('share') == 'false':
        get_params.pop('share')
        share_button_url = urlparse.urljoin(
            settings.BASE_URL_FULL,
            '/share/item/?%s' % urllib.urlencode(get_params))
    else:
        share_links = util.get_share_links(share_url, item.name)

    # render the page
    return util.render_to_response(
        request, 'playback.html',
        {'item': item,
         'channel': channel,
         'previous': previous,
         'next': next,
         'embed': util.mark_safe(playback.embed_code(item)),
         'feed_url': feed_url,
         'webpage_url': webpage_url,
         'item_name': item_name,
         'share_url': share_url,
         'share_button_url': share_button_url,
         'share_type': 'item',
         'google_analytics_ua': None,
         'share_links': share_links})


def email(request):
    share_form = ShareForm(request.POST)

    if not share_form.is_valid():
        return util.render_to_response(
            request, 'share-form.html',
            {'share_form': share_form,
             'share_type': share_form.data.get('share_type'),
             'feed_url': share_form.data.get('feed_url'),
             'file_url': share_form.data.get('file_url'),
             'share_url': share_form.data.get('share_url'),
             'item_url': share_form.data.get('item_url')})

    # construct the email to send out from a template
    if share_form.cleaned_data['share_type'] == 'feed':
        title = _(u'%(from_email)s wants to share a video feed with you') % {
            'from_email': share_form.cleaned_data['from_email']}
    else:
        title = _(u'%(from_email)s wants to share a video with you') % {
            'from_email': share_form.cleaned_data['from_email']}

    email_template = loader.get_template('guide/share-email.txt')
    email_body = email_template.render(Context(share_form.cleaned_data))

    util.send_mail(
        title, email_body,
        share_form.cleaned_data['recipients'],
        #share_form.cleaned_data['from_email'],
        break_lines=False)

    return util.render_to_response(
        request, 'share-email-success.html', {})
