# Copyright (c) 2008-2009 Participatory Culture Foundation
# See LICENSE for details.

import urlparse
from datetime import datetime, timedelta

from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist
from django.contrib.auth.models import User
from django.contrib.syndication import feeds, views
from django.utils import feedgenerator
from django.views.decorators.cache import cache_page
from django.http import Http404

from channelguide.api import utils as api_utils
from channelguide import util

def https_add_domain(domain, url):
    """
    The built-in add_domain doesn't support https:// URLs, so we fake it.
    """
    if url and url.startswith('https://'):
        return url
    return _old_add_domain(domain, url)


_old_add_domain = feeds.add_domain
feeds.add_domain = https_add_domain


class MiroFeedGenerator(feedgenerator.DefaultFeed):
    thumbnail_url = "http://s3.getmiro.com/img/home-logo-revised.png"

    def write_items(self, handler):
        handler.startElement(u"image", {})
        handler.addQuickElement(u"url", self.thumbnail_url)
        handler.addQuickElement(u"title", self.feed['title'])
        handler.addQuickElement(u"link", self.feed['link'])
        handler.endElement(u"image")
        feedgenerator.DefaultFeed.write_items(self, handler)

    def add_item_elements(self, handler, item):
        feedgenerator.DefaultFeed.add_item_elements(self, handler, item)
        handler.addQuickElement('thumbnail', item['thumbnail'])


class ChannelsFeed(feeds.Feed):
    title_template = "feeds/channel_title.html"
    description_template = "feeds/channel_description.html"
    feed_type = MiroFeedGenerator

    def item_extra_kwargs(self, item):
        return {
            'thumbnail': util.make_absolute_url(item.thumb_url_200_134())
            }

    def item_guid(self, item):
        if item.newest:
            return item.newest.guid or item.newest.url

    def item_pubdate(self, item):
        if item.newest:
            return item.newest.date

    def item_enclosure_url(self, item):
        max_date = self.get_date_for_item(item)
        if not max_date:
            item.newest = None
            return
        results = item.items.filter(
            date__isnull=False,
            date__lt=max_date)
        if results.count():
            item.newest = results.order_by('-date')[0]

            # We shouldn't produce a redirect-enclosure for anything that
            # ends in .swf or comes from youtube (since youtube also
            # sometimes does its own redirects, so just .swf doesn't always
            # work) because that will make it so that miro doesn't know
            # that it should do flash scraping (needs to see actual item
            # url to do flash scraping)
            split_url = urlparse.urlsplit(item.newest.url)
            if (split_url[2].endswith('.swf')
                    or split_url[1] in ('www.youtube.com', 'youtube.com')):
                return item.newest.url
            else:
                return item.get_absolute_url() + '/latest'

        else:
            item.newest = None

    def item_enclosure_length(self, item):
        if item.newest and item.newest.size:
            return item.newest.size
        else:
            return ""

    def item_enclosure_mime_type(self, item):
        if item.newest:
            return item.newest.mime_type

    def get_date_for_item(self, item):
        # default to last Sunday; keeps us from having more than one new show a
        # week
        now = datetime.now()
        return (now - timedelta(days=now.isoweekday())).replace(
            hour=0, minute=0, second=0, microsecond=0)


class FeaturedChannelsFeed(ChannelsFeed):
    title = "Featured Channel Previews from Miro"
    link = "/featured/"
    description = "Featured channels on the Miro Guide."

    def items(self):
        return api_utils.get_feeds(self.request, 'featured', True,
                                   limit=20)


    def get_date_for_item(self, item):
        return item.featured_at


class NewChannelsFeed(ChannelsFeed):
    title = 'New in Miro Previews'
    link = "/new/"
    description = "The newest channels on the Miro Guide."

    def items(self):
        return api_utils.get_feeds(self.request, 'name', None,
                                   sort='-age', limit=20)


    def get_date_for_item(self, item):
        return item.approved_at


class PopularChannelsFeed(ChannelsFeed):
    title = 'Popular Channel Previews from Miro'
    link = "/popular/"
    description = "The most popular channels on the Miro Guide."

    def items(self):
        return api_utils.get_feeds(self.request, 'name', None,
                                   sort='-popular', limit=20)


class TopRatedChannelsFeed(ChannelsFeed):
    title = 'Top Rated Channel Previews from Miro'
    link = "/toprated/"
    description = "The highest rated channels on the Miro Guide."

    def items(self):
        return api_utils.get_feeds(self.request, 'name', None,
                                   sort='-rating', limit=20)


class FilteredFeed(ChannelsFeed):
    model = None
    filter = None

    def get_object(self, bits):
        if len(bits) != 1:
            raise ObjectDoesNotExist
        return bits[0]

    def title(self, obj):
        return 'Newest %s Channel Previews from Miro' % obj.encode('utf8')

    def link(self, obj):
        if obj is None:
            raise Http404
        return self.base + obj

    def description(self, obj):
        if obj is None:
            return ''
        return 'The newest %s channels in the Miro Guide' % obj.encode('utf8')

    def items(self, obj):
        if obj is None:
            return ''
        return api_utils.get_feeds(self.request, self.filter, obj,
                                   sort='-age', limit=20)

    def get_date_for_item(self, item):
        return item.approved_at


class CategoriesFeed(FilteredFeed):
    base = '/genres/'
    filter = 'category'


class TagsFeed(FilteredFeed):
    base = '/tags/'
    filter = 'tag'


class LanguagesFeed(FilteredFeed):
    base = '/languages/'
    filter = 'language'


class SearchFeed(ChannelsFeed):

    def get_object(self, bits):
        if len(bits) != 1:
            raise ObjectDoesNotExist
        terms = bits[0].split('+')
        return terms

    def title(self, obj):
        return 'Search Feed: %s' % ' '.join(obj)

    def link(self, obj):
        if obj is None:
            raise Http404
        return settings.BASE_URL_FULL + 'search?query=' + '+'.join(obj)

    def description(self, obj):
        if obj is None:
            return ''
        return 'Channels that match "%s"' % ' '.join(obj)

    def items(self, obj):
        if obj is None:
            return ''
        return api_utils.search(obj)


class RecommendationsFeed(ChannelsFeed):

    def get_object(self, bits):
        if len(bits) != 2:
            raise ObjectDoesNotExist
        username, password = bits
        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            raise ObjectDoesNotExist
        if user.check_password(password):
            return user
        else:
            raise ObjectDoesNotExist

    def title(self, user):
        return 'Recommended Channels for %s from Miro' % user.username

    def description(self, user):
        return 'These channels are recommended for \
%s based on their ratings in the Miro Guide' % user.username

    def link(self):
        return settings.BASE_URL_FULL + '/recommend/'

    def items(self, user):
        return api_utils.get_recommendations(user)


cached_feed =  cache_page(views.feed, 3600)
