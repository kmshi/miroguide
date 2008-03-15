# Copyright (c) 2008 Participatory Culture Foundation
# See LICENSE for details.

from channelguide import init
init.init_external_libraries()
from sqlhelper.sql.expression import NULL
from channelguide import db, util
from channelguide.guide import api
from channelguide.guide.models import Channel, Category, Tag, Language, FeaturedQueue
from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist
from django.contrib.syndication import feeds
from django.http import Http404

from operator import attrgetter

def https_add_domain(domain, url):
    """
    The built-in add_domain doesn't support https:// URLs, so we fake it.
    """
    if url.startswith('https://'):
        return url
    return _old_add_domain(domain, url)

_old_add_domain = feeds.add_domain
feeds.add_domain = https_add_domain

class ChannelsFeed(feeds.Feed):
    title_template = "feeds/channel_title.html"
    description_template = "feeds/channel_description.html"

    def item_enclosure_url(self, item):
        item.join('items').execute(self.request.connection)
        results = [i for i in item.items.records[:] if i.date is not None]
        if results:
            results.sort(key=attrgetter('date'), reverse=True)
            items.newest = results[0]
            return item.newest.url
        else:
            item.newest = None

    def item_enclosure_length(self, item):
        if item.newest:
            return item.newest.size

    def item_enclosure_mime_type(self, item):
        if item.results:
            return item.newest.mime_type

class FeaturedChannelsFeed(ChannelsFeed):
    title = "Featured Channels"
    link = "/channels/features"
    description = "Featured channels on the Miro Guide."

    def items(self):
        query = Channel.query().join('featured_queue')
        j = query.joins['featured_queue']
        j.where(j.c.state==1)
        query.order_by(j.c.state).order_by(j.c.featured_at, desc=True)
        return query.execute(self.request.connection)

class NewChannelsFeed(ChannelsFeed):
    title = 'Newest Channels'
    link = "/channels/recent"
    description = "The newest channels on the Miro Guide."

    def items(self):
        query = Channel.query_new().limit(10)
        return query.execute(self.request.connection)

class FilteredFeed(ChannelsFeed):
    model = None
    filter = None

    def get_object(self, bits):
        if len(bits) != 1:
            raise ObjectDoesNotExist
        try:
            obj = util.get_object_or_404_by_name(self.request.connection,
                    self.model, bits[0])
        except Exception:
            raise ObjectDoesNotExist
        return obj

    def title(self, obj):
        return 'Newest Channels in %s' % obj.name.encode('utf8')

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
        query = Channel.query_new().join(self.filter).limit(10)
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

