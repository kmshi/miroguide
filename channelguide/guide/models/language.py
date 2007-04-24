from channelguide import util
from channelguide.db import DBObject

class Language(DBObject):
    """Languages are names for the different languages a channel can be in.
    NOTE: we purposely don't associate languages with ISO codes.  ISO codes
    are for written language, which is distinct from spoken language.
    (for example: Mandarin and Cantonese).
    """
    def __init__(self, name=None):
        self.name = name

    def get_absolute_url(self):
        return util.make_url('languages/%d' % self.id)

    def link(self):
        return util.make_link(self.get_absolute_url(), str(self))

    def get_channel_count(self):
        return (self.channel_count_primary +
                self.channel_count_secondary)

    channel_count = property(get_channel_count)

    def __str__(self):
        return self.name

    def __repr__(self):
        return '%s(%r)' % (self.__class__.__name__, self.name)
