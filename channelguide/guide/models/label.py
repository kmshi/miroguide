# Copyright (c) 2008 Participatory Culture Foundation
# See LICENSE for details.

"""labels.py contains labels that are attached to channels.  This includes
categories which are defined by the moderaters and tags which are
user-created.
"""

from channelguide import util
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
        return util.make_url('genres/%s' % self.name.encode('utf8'))

    def get_rss_feed(self):
        return util.make_url('feeds/genres/%s' % self.name.encode('utf8'))

class Tag(Label):
    """Tags are user created labels.  Any string of text can be a tag and any
    user can tag any channel.
    """
    table = tables.tag

    def get_url(self):
        return util.make_url('tags/%s' % self.name.encode('utf8'))

    def get_rss_feed(self):
        return util.make_url('feeds/tags/%s' % self.name.encode('utf8'))

class CategoryMap(Record):
    table = tables.category_map

class TagMap(Record):
    table = tables.tag_map

    def __init__(self, channel, user, tag):
        self.channel_id = channel.id
        self.user_id = user.id
        self.tag_id = tag.id
