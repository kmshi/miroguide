# Copyright (c) 2008-2009 Participatory Culture Foundation
# See LICENSE for details.

"""labels.py contains labels that are attached to channels.  This includes
categories which are defined by the moderaters and tags which are
user-created.
"""

import random

from channelguide import util
from channelguide import cache
from channelguide.guide import tables
from sqlhelper.orm import Record

class Label(Record):
    """Label is the base class for both Category and Tag."""
    def __init__(self, name):
        self.name = name

    def link(self):
        return util.make_link(self.get_url(), self.name)

    def __unicode__(self):
        return self.name

    def __len__(self):
        return len(self.name)

    def __repr__(self):
        return '%s(%r)' % (self.__class__.__name__, self.name)

    def get_absolute_url(self):
        return util.make_absolute_url(self.get_url())


class Category(Label):
    """Categories are created by the admins and assigned to a channel by that
    channel's submitter.
    """
    table = tables.category

    def get_url(self):
        return util.make_url('genres/%s' % self.name.encode('utf8'),
                             ignore_qmark=True)

    def get_rss_url(self):
        return util.make_url('feeds/genres/%s' % self.name.encode('utf8'),
                             ignore_qmark=True)

    def get_list_channels(self, connection, filter_front_page=False):
        def _q(filter_by_rating):
            from channelguide.guide.models import Channel
            query = Channel.query_approved(archived=0)
            query.join("categories", 'stats')
            query.where(query.c.id.in_(c.id for c in self.channels))
            if filter_by_rating:
                query.join('rating')
                query.where(query.joins['rating'].c.average > 4)
                query.where(query.joins['rating'].c.count > 4)
            query.order_by(query.joins['stats'].c.subscription_count_today, desc=True)
            query.cacheable = cache.client
            query.cacheable_time = 3600
            channels = query.execute(connection)
            if filter_front_page:
                return [channel for channel in channels
                        if channel.can_appear_on_frontpage()]
            else:
                return channels

        most_popular = _q(True)
        if len(most_popular) < 2:
            most_popular = _q(False)
        return most_popular[0], random.choice(most_popular[1:])

class Tag(Label):
    """Tags are user created labels.  Any string of text can be a tag and any
    user can tag any channel.
    """
    table = tables.tag

    def get_url(self):
        return util.make_url('tags/%s' % self.name.encode('utf8'),
                             ignore_qmark=True)

    def get_rss_url(self):
        return util.make_url('feeds/tags/%s' % self.name.encode('utf8'),
                             ignore_qmark=True)

class CategoryMap(Record):
    table = tables.category_map

class TagMap(Record):
    table = tables.tag_map

    def __init__(self, channel, user, tag):
        self.channel_id = channel.id
        self.user_id = user.id
        self.tag_id = tag.id
