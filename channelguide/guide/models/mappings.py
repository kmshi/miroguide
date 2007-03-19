"""mappings.py

Conntains all the SQLALchemy mapper() calls that we use.  Having them all in
one module allows us to define all the classes used, then map them all at
once.  This is makes circular references not a problem (for example between
Channel.channels and Item.item).
"""

from sqlalchemy import (mapper, relation, MapperExtension, and_, select, func,
        backref)

from channelguide.db import dbutil
from channelguide.guide import tables
from blogtrack import PCFBlogPost
from label import Category, Tag, TagMap
from language import Language
from user import User
from item import Item
from note import ChannelNote, ModeratorPost
from search import ItemSearchData, ChannelSearchData
from channel import Channel

# channels
class ChannelMapperExtension(MapperExtension):
    """Hook into the mapper for Channel objects to delete their subscription
    data.
    """

    def before_delete(self, mapper, connection, instance):
        delete = tables.channel_subscription.delete(
                tables.channel_subscription.c.channel_id==instance.id)
        connection.execute(delete)
        instance._subscriptions = None
channel_select = select([tables.channel,
    dbutil.count_subquery('item_count', tables.item),
    dbutil.count_subquery('subscription_count', tables.channel_subscription),
    dbutil.count_subquery('subscription_count_today', 
        tables.channel_subscription,
        'timestamp > DATE_SUB(NOW(), INTERVAL 1 DAY)'),
    dbutil.count_subquery('subscription_count_month', 
        tables.channel_subscription,
        'timestamp > DATE_SUB(NOW(), INTERVAL 1 MONTH)'),
    ])
mapper(Channel, channel_select.alias(),
        extension=ChannelMapperExtension(), properties={
        'items': relation(Item, private=True, backref='channel'),
        'language': relation(Language),
        'secondary_languages': relation(Language,
            secondary=tables.secondary_language_map),
        'search_data': relation(ChannelSearchData, private=True,
            uselist=False, backref='channel'),
    })
# items
mapper(Item, tables.item, properties={
        'search_data': relation(ItemSearchData, private=True, uselist=False,
            backref='item'),
    })
# search data
mapper(ChannelSearchData, tables.channel_search_data)
mapper(ItemSearchData, tables.item_search_data)
# users
user_select = select([tables.user,
    dbutil.aggregate_subquery('moderator_action_count',
        dbutil.count_distinct(tables.moderator_action.c.channel_id),
        tables.moderator_action),
    ])
user_mapper = mapper(User, user_select.alias(), properties={
    'channels': relation(Channel, private=True, backref='owner')
    })
# categories
category_select = select([tables.category,
    dbutil.count_subquery('channel_count', 
        tables.category_map.join(tables.channel),
        tables.channel.c.state=='A')
    ])
mapper(Category, category_select.alias(), properties={
    'channels': relation(Channel, secondary=tables.category_map,
        backref='categories'),
    })
# tags
tag_select = select([tables.tag,
    dbutil.aggregate_subquery('user_count',
        dbutil.count_distinct(tables.tag_map.c.user_id), tables.tag_map),
    dbutil.aggregate_subquery('channel_count',
        dbutil.count_distinct(tables.tag_map.c.channel_id),
        tables.tag_map.join(tables.channel),
        tables.channel.c.state == Channel.APPROVED),
    ])
mapper(Tag, tag_select.alias(), properties={
    'channels': relation(Channel, secondary=tables.tag_map,
        backref=backref('tags', viewonly=True)),
    })
mapper(TagMap, tables.tag_map, properties={
    'tag': relation(Tag),
    'user': relation(User, backref=backref('tags', private=True)),
    'channel': relation(Channel, backref=backref('tag_maps', private=True)),
    })
# languages
language_select = select([tables.language,
    dbutil.count_subquery('channel_count_primary', tables.channel,
        tables.channel.c.state == 'A'),
    select([func.count('*')], 
        and_(tables.secondary_language_map.c.language_id==tables.language.c.id,
            tables.channel.c.state == 'A'),
        from_obj=[tables.secondary_language_map.join(tables.channel)], scalar=True
        ).label('channel_count_secondary'),
    ])
mapper(Language, language_select.alias())
# notes
mapper(ModeratorPost, tables.moderator_post, properties={
        'user': relation(User, backref=backref('moderator_posts',
            private=True)),
        })
mapper(ChannelNote, tables.channel_note, properties={
        'channel': relation(Channel, backref=backref('notes', private=True)),
        'user': relation(User, backref=backref('notes', private=True)),
        })
# blog posts
mapper(PCFBlogPost, tables.pcf_blog_post)
