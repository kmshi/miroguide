from sqlalchemy import mapper, and_, select, func

import tables as t
from channelguide.channels.tables import channel, secondary_language_map
from channelguide import util

class Language(object):
    """Languages are names for the different languages a channel can be in.
    NOTE: we purposely don't associate languages with ISO codes.  ISO codes
    are for written language, which is distinct from spoken language.
    (for example: Mandarin and Cantonese).
    """
    def __init__(self, name=None):
        self.name = name

    def get_absolute_url(self):
        return util.make_absolute_url('languages/%d' % self.id)

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

language_select = select([t.language,
    util.count_subquery('channel_count_primary', channel,
        channel.c.state == 'A'),
    select([func.count('*')], 
        and_(secondary_language_map.c.language_id == t.language.c.id,
            channel.c.state == 'A'),
        from_obj=[secondary_language_map.join(channel)], scalar=True
        ).label('channel_count_secondary'),
    ])

mapper(Language, language_select.alias())
