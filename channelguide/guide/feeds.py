from channelguide import init
init.init_external_libraries()
from channelguide import db, util
from channelguide.guide.models import Channel, Category
from django.core.exceptions import ObjectDoesNotExist
from django.contrib.syndication.feeds import Feed

class ChannelsFeed(Feed):
    title_template = "feeds/channel_title.html"
    description_template = "feeds/channel_description.html"

class NewChannelsFeed(ChannelsFeed):
    title = 'Newest Channels'
    link = "/feeds/new/"
    description = "The newest channels on the Miro Guide."

    def items(self):
        connection = db.connect()
        query = Channel.query_new().limit(10)
        items = query.execute(connection)
        connection.close()
        return items

class CategoriesFeed(ChannelsFeed):

    def get_object(self, bits):
        connection = db.connect()
        if len(bits) != 1:
            raise ObjectDoesNotExist
        print 'getting object for', bits
        try:
            obj = util.get_object_or_404_by_name(connection, Category, bits[0])
        except Exception:
            raise ObjectDoesNotExist
        connection.close()
        return obj

    def title(self, obj):
        return 'Newest Channels in %s' % obj.name

    def link(self, obj):
        return '/feeds/categories/%s/' % obj.name

    def description(self, obj):
        return 'The newest %s channels in the Miro Guide' % obj.name

    def items(self, obj):
        connection = db.connect()
        query = Channel.query_new().join('categories').limit(10)
        query.joins['categories'].where(id=obj.id)
        items = query.execute(connection)
        connection.close()
        return items

