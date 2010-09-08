# Copyright (c) 2008-2009 Participatory Culture Foundation
# See LICENSE for details.

import logging
import datetime
import sha
import os.path
import urllib
import urlparse
import re

import feedparser
from django.core.mail import EmailMultiAlternatives
from django.conf import settings
from django.core import cache
from django.core.paginator import Paginator
from django.http import HttpResponse
from django.shortcuts import render_to_response
from django.template import loader, RequestContext, Context
from django.utils.translation import ugettext as _

from channelguide import util
from channelguide.guide import filetypes, feedutil
from channelguide.sharing.forms import ShareForm
from channelguide.channels.models import (Channel, Item)


# Custom exceptions for this module
class Error(Exception): pass
class FeedFetchingError(Error): pass


def strip_tags(description):
    return re.sub(r'<[^>]+?>', '', description)

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

    def thumb_url_97_65(self):
        return self.thumbnail_url

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
        self.state = Channel.APPROVED

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


def get_channels_and_items(feed_url):
    feed_sha1 = sha.sha(feed_url).hexdigest()
    feed_key = 'share_feed-' + feed_sha1
    items_key = 'share_feed_items-' + feed_sha1

    # check the cache.  If not...
    cached_channel = cache.cache.get(feed_key)
    cached_items = cache.cache.get(items_key)
    if cached_channel:
        channel = cached_channel
        items = cached_items
    else:
        # check to see if we have that feed in our database...
        try:
            channel = Channel.objects.get(url=feed_url)
        except Channel.DoesNotExist:
            ## parse the feed
            try:
                parsed = feedparser.parse(feed_url)
            except Exception:
                logging.exception('error parsing %s' % feed_url)
                raise FeedFetchingError('feedparser error while parsing')

            #ok, so this doesn't work...
            if hasattr(parsed, 'status') and parsed.status != 200:
                raise FeedFetchingError(
                    "Got a non-200 status while parsing feed")

            if parsed.bozo: # this didn't work either
                raise FeedFetchingError('Feed is unparsable')

            ## generate fake channel
            thumbnail_url = (
                settings.STATIC_BASE_URL + 'images/generic_feed_thumb.png')

            channel = FakeChannel(
                parsed.feed.get('title', ''),
                parsed.feed.get('subtitle', ''),
                feed_url,
                parsed.feed.get('link', ''),
                thumbnail_url)

            items = []
            # why not limit the number of items here to 4?
            # Because we might need to check to see if a particular
            # item is in this feed if it's being faked...
            for entry in parsed.entries:
                enclosure = feedutil.get_first_video_enclosure(entry)
                link = None
                if enclosure is not None and 'href' in enclosure:
                    link = enclosure['href']
                if not link:
                    if not entry.get('link'):
                        continue
                    link = entry.link

                updated_datetime = None
                if entry.get('updated_parsed'):
                    updated_datetime = datetime.datetime(
                        *entry.updated_parsed[:7])
                if 'title' not in entry and not (
                    'summary' in entry or 'description' in entry):
                    continue
                item = FakeItem(
                    link,
                    entry.title,
                    entry.get('summary', entry.get('description', '')),
                    updated_datetime,
                    thumbnail_url) # just use whatever thumbnail the channel
                                   # has?
                items.append(item)
        else:
            items = channel.items.all()[:4]

        cache.cache.set(feed_key, channel)
        cache.cache.set(items_key, items)

    return channel, items

def get_item(file_url, channel, channel_items, item_name):
    item = next = previous = None
    # see if we have that item in the feed
    ## if it's a fake feed check the full list of items
    if isinstance(channel, FakeChannel):
        i = 0
        if channel_items:
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
    elif channel is not None:
        try:
            item = Item.objects.get(channel=channel, url=file_url)
        except Item.DoesNotExist:
            item = None

    ## if we don't have an item at this point, we need to generate
    ## a fake one.  It won't have much useful info though...
    if item is None:
        if not item_name:
            subpath = urlparse.urlsplit(file_url)[2]
            if len(subpath) > 1:
                item_name = subpath.split('/')[-1]

            else:
                item_name = file_url

        item = FakeItem(file_url, item_name)

    return previous, item, next

def share_feed(request):
    try:
        feed_url = request.GET['feed_url'].encode('utf8')
    except KeyError:
        return HttpResponse("you must supply a feed_url")

    try:
        channel, items = get_channels_and_items(feed_url)
    except FeedFetchingError:
        return HttpResponse("This feed appears to be dead.")

    if isinstance(channel, Channel):
        return util.redirect(channel.get_absolute_url(), {'share': 'true'})

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

    if items:
        item_paginator = Paginator(items[:10], 10)
        item_page = item_paginator.page(1)
    else:
        item_page = None
    return render_to_response('channels/show-channel.html',
                              {'channel': channel,
                               'item_page': item_page,
                               'feed_url': feed_url,
                               'share_url': share_url,
                               'share_button_url': share_button_url,
                               'share_type': 'feed',
                               'google_analytics_ua': None,
                               'share_links': share_links
                               }, context_instance=RequestContext(request))


def share_item(request):
    # check to see if we have that item in our database...
    # If so
    #   use that item
    # else
    #   let's create a "fake" item to preview
    # render that item preview
    try:
        file_url = request.GET['file_url'].encode('utf8')
    except KeyError:
        return HttpResponse("you must supply a file_url")

    feed_url = request.GET.get('feed_url')
    webpage_url = request.GET.get('webpage_url')
    item_name = request.GET.get('item_name')

    channel = None
    item = None
    next = None
    previous = None

    if webpage_url:
        webpage_url = webpage_url.encode('utf8')

    if feed_url:
        feed_url = feed_url.encode('utf8')
        try:
            channel, channel_items = get_channels_and_items(feed_url)
        except FeedFetchingError:
            channel = None
            feed_url = None
    if channel is None:
        channel_items = []

    previous, item, next = get_item(file_url, channel,
                                    channel_items, item_name)

    if isinstance(item, Item):
        return util.redirect(item.get_absolute_url(), {'share': 'true'})

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
    return render_to_response(
        'channels/playback.html',
        {'item': item,
         'channel': channel,
         'audio': False,
         'previous': previous,
         'next': next,
         'feed_url': feed_url,
         'webpage_url': webpage_url,
         'item_name': item_name,
         'file_url': file_url,
         'share_url': share_url,
         'share_button_url': share_button_url,
         'share_type': 'item',
         'google_analytics_ua': None,
         'share_links': share_links},
        context_instance=RequestContext(request))

def _image(name):
    return os.path.join(settings.STATIC_DIR, 'images', name)

def email(request):
    share_form = ShareForm(request.POST)

    if not share_form.is_valid():
        return render_to_response(
            'sharing/form.html',
            {'share_form': share_form,
             'share_type': share_form.data.get('share_type'),
             'feed_url': share_form.data.get('feed_url'),
             'file_url': share_form.data.get('file_url'),
             'share_url': share_form.data.get('share_url'),
             'item_url': share_form.data.get('item_url')},
            context_instance=RequestContext(request))

    # construct the email to send out from a template
    if share_form.cleaned_data['share_type'] == 'feed':
        subject = _(u'%(from_email)s wants to share a video feed with you') % {
            'from_email': share_form.cleaned_data['from_email']}
        try:
            channel, channel_items = get_channels_and_items(
                share_form.cleaned_data['feed_url'])
        except FeedFetchingError:
            title = description = thumbnail =None
        else:
            title = channel.name
            description = channel.description
            if hasattr(channel, 'thumbnail_url'):
                thumbnail = channel.thumbnail_url
            else:
                thumbnail = channel.thumb_url_200_134()
    else:
        subject = _(u'%(from_email)s wants to share a video with you') % {
            'from_email': share_form.cleaned_data['from_email']}
        if share_form.cleaned_data['feed_url']:
            try:
                channel, channel_items = get_channels_and_items(
                    share_form.cleaned_data['feed_url'])
            except FeedFetchingError:
                channel = channel_items = None
        else:
            channel = channel_items = None
        previous, item, next = get_item(share_form.cleaned_data['file_url'],
                                        channel, channel_items, None)
        title = item.name
        description = item.description
        if item:
            if hasattr(item, 'thumbnail_url'):
                thumbnail = item.thumbnail_url
            else:
                thumbnail = item.thumb_200_134()
        elif channel:
            if hasattr(channel, 'thumbnail_url'):
                thumbnail = channel.thumbnail_url
            else:
                thumbnail = channel.thumb_url_200_134()
        else:
            thumbnail = None

    if description:
        description = strip_tags(description)
        if len(description) > 170:
            description = description[:167] + '...'

    context = share_form.cleaned_data
    context.update({'title': title,
                    'description': description})
    if thumbnail:
        context['thumbnail'] = util.make_absolute_url(thumbnail)

    email_template = loader.get_template('sharing/email-body.txt')
    email_body = email_template.render(Context(context))

    html_template = loader.get_template('sharing/email-body.html')
    html_body = html_template.render(Context(context))

    for recipient in share_form.cleaned_data['recipients']:
        message = EmailMultiAlternatives(
            subject, email_body, to=[recipient])
        message.attach_alternative(html_body, 'text/html')
        message.send()

    return render_to_response(
        'sharing/email-success.html', {},
        context_instance=RequestContext(request))
