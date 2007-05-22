"""labels.py contains labels that are attached to channels.  This includes
categories which are defined by the moderaters and tags which are
user-created.
"""

from channelguide import util
from channelguide.guide import tables
from sqlhelper.orm import Record
from sqlhelper.sql import Select

class Label(Record):
    """Label is the base class for both Category and Tag."""
    def __init__(self, name):
        self.name = name

    @classmethod
    def query_with_count(cls):
        query = cls.query()
        count_subquery = Select()
        select.add_column("COUNT(*)")
        select.add_from(tables.channel.name)
        join_column = cls.table.find_foreign_key(tables.channel)
        select.add_where(join_column==join_column.ref)
        select.add_where(tables.channel.c.state=='A')

    def link(self):
        return util.make_link(self.get_absolute_url(), str(self))

    def __str__(self):
        return self.name

    def __repr__(self):
        return '%s(%r)' % (self.__class__.__name__, self.name)

class Category(Label):
    """Categories are created by the admins and assigned to a channel by that
    channel's submitter.
    """
    table = tables.category

    def get_absolute_url(self):
        return util.make_url('categories/%d' % self.id)

class Tag(Label):
    """Tags are user created labels.  Any string of text can be a tag and any
    user can tag any channel.
    """
    table = tables.tag

    def get_absolute_url(self):
        return util.make_url('tags/%d' % self.id)

class CategoryMap(Record):
    table = tables.category_map

class TagMap(Record):
    table = tables.tag_map

    def __init__(self, channel, user, tag):
        self.channel_id = channel.id
        self.user_id = user.id
        self.tag_id = tag.id
