from channelguide import init
init.init_external_libraries()
from channelguide import db, util
from channelguide.guide.models import Channel, Category, FeaturedQueue
from django.core.exceptions import ObjectDoesNotExist
from django.contrib.syndication import feeds

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
        if item.items:
            return item.items[0].url

    def item_enclosure_length(self, item):
        if item.items:
            return item.items[0].size

    def item_enclosure_mime_type(self, item):
        if item.items:
            return item.items[0].mime_type

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

class CategoriesFeed(ChannelsFeed):

    def get_object(self, bits):
        if len(bits) != 1:
            raise ObjectDoesNotExist
        try:
            obj = util.get_object_or_404_by_name(self.request.connection,
                    Category, bits[0])
        except Exception:
            raise ObjectDoesNotExist
        return obj

    def title(self, obj):
        return 'Newest Channels in %s' % obj.name.encode('utf8')

    def link(self, obj):
        return obj.get_url()

    def description(self, obj):
        return 'The newest %s channels in the Miro Guide' % obj.name.encode('utf8')

    def items(self, obj):
        query = Channel.query_new().join('categories').limit(10)
        query.joins['categories'].where(id=obj.id)
        return query.execute(self.request.connection)
