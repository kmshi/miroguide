# Copyright (c) 2008 Participatory Culture Foundation
# See LICENSE for details.

import urlparse

from channelguide import init
init.init_external_libraries()
from channelguide import util
from channelguide.guide import api
from channelguide.guide.models import Channel, Category, Tag, Language, User
from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist
from django.contrib.syndication import feeds
from django.utils import feedgenerator
from django.http import Http404

from operator import attrgetter

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

class ChannelsFeed(feeds.Feed):
    title_template = "feeds/channel_title.html"
    description_template = "feeds/channel_description.html"
    feed_type = MiroFeedGenerator

    def item_guid(self, item):
        if item.newest:
            return item.newest.guid or item.newest.url

    def item_enclosure_url(self, item):
        item.join('items').execute(self.request.connection)
        results = [i for i in item.items.records[:] if i.date is not None]
        if results:
            results.sort(key=attrgetter('date'), reverse=True)
            item.newest = results[0]

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
                return util.make_absolute_url('channels/latest/%i' % item.id)
        else:
            item.newest = None

    def item_enclosure_length(self, item):
        if item.newest:
            return item.newest.size

    def item_enclosure_mime_type(self, item):
        if item.newest:
            return item.newest.mime_type


class FeaturedChannelsFeed(ChannelsFeed):
    title = "Featured Channel Previews from Miro"
    link = "/featured/"
    description = "Featured channels on the Miro Guide."

    def items(self):
        return api.get_channels(self.request.connection, 'featured', True,
                                limit=20)


class NewChannelsFeed(ChannelsFeed):
    title = 'New in Miro Previews'
    link = "/new/"
    description = "The newest channels on the Miro Guide."

    def items(self):
        return api.get_channels(self.request.connection, 'name', None,
                                sort='-age', limit=20)


class PopularChannelsFeed(ChannelsFeed):
    title = 'Popular Channel Previews from Miro'
    link = "/popular/"
    description = "The most popular channels on the Miro Guide."

    def items(self):
        return api.get_channels(self.request.connection, 'name', None,
                                sort='-popular', limit=20)


class TopRatedChannelsFeed(ChannelsFeed):
    title = 'Top Rated Channel Previews from Miro'
    link = "/toprated/"
    description = "The highest rated channels on the Miro Guide."

    def items(self):
        return api.get_channels(self.request.connection, 'name', None,
                                sort='-rating', limit=20)


class FilteredFeed(ChannelsFeed):
    model = None
    filter = None

    def get_object(self, bits):
        if len(bits) != 1:
            raise ObjectDoesNotExist
        try:
            obj = util.get_object_or_404_by_name(self.request.connection,
                    self.model, bits[0])
        except Http404:
            raise ObjectDoesNotExist
        return obj

    def title(self, obj):
        return 'Newest %s Channel Previews from Miro' % obj.name.encode('utf8')

    def link(self, obj):
        if obj is None:
            raise Http404
        return obj.get_url()

    def description(self, obj):
        if obj is None:
            return ''
        return 'The newest %s channels in the Miro Guide' % obj.name.encode('utf8')

    def items(self, obj):
        if obj is None:
            return ''
        query = Channel.query_new().join(self.filter).limit(20)
        query.joins[self.filter].where(id=obj.id)
        return query.execute(self.request.connection)


class CategoriesFeed(FilteredFeed):
    model = Category
    filter = 'categories'


class TagsFeed(FilteredFeed):
    model = Tag
    filter = 'tags'


class LanguagesFeed(FilteredFeed):
    model = Language

    def items(self, obj):
        if obj is None:
            return ''
        query = Channel.query_new().join('secondary_languages').limit(10)
        query.where((Channel.c.primary_language_id==obj.id) |
                Language.secondary_language_exists_where(obj.id))
        return query.execute(self.request.connection)


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
        return api.search(self.request.connection, obj)


class RecommendationsFeed(ChannelsFeed):

    def get_object(self, bits):
        if len(bits) != 2:
            raise ObjectDoesNotExist
        username, password = bits
        try:
            user = User.query(username=username).get(self.request.connection)
        except LookupError:
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
        return api.get_recommendations(self.request.connection,
                                       user)
