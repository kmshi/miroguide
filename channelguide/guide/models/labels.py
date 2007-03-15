"""labels.py contains labels that are attached to channels.  This includes
categories which are defined by the moderaters and tags which are
user-created.
"""

from channelguide.db import DBObject

class Label(DBObject):
    """Label is the base class for both Category and Tag."""
    def __init__(self, name=None):
        self.name = name

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
    def get_absolute_url(self):
        return util.make_absolute_url('categories/%d' % self.id)

class Tag(Label):
    """Tags are user created labels.  Any string of text can be a tag and any
    user can tag any channel.
    """
    def get_absolute_url(self):
        return util.make_absolute_url('tags/%d' % self.id)

class TagMap(object):
    def __init__(self, channel, user, tag):
        self.channel_id = channel.id
        self.user_id = user.id
        self.tag_id = tag.id
