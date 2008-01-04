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
    link = "/channels/recent"
    description = "The newest channels on the Miro Guide."

    def items(self):
        import logging
        logging.info(self.title_template_name)
        logging.info(self.description_template_name)
        query = Channel.query_new().limit(10)
        items = query.execute(self.request.connection)
        logging.info(repr(items))
        return items

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
        items = query.execute(self.request.connection)
        return items

