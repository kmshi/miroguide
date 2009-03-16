# Copyright (c) 2009 Participatory Culture Foundation
# See LICENSE for details.

from channelguide.guide import tables
from channelguide.guide.models import Channel, Item
from sqlhelper.orm import record

class WatchedVideos(record.Record):
    table = tables.watched_videos

    # values for type
    TOTAL = 0
    CHANNEL = 1
    ITEM = 2
    
    def __init__(self, type, id):
        self.type = type
        self.id = id
        self.count = 0

    @classmethod
    def get_or_new(klass, connection, (type, id)):
        try:
            return klass.get(connection, (type, id))
        except LookupError:
            return klass(type, id)

    @classmethod
    def count(klass, connection, type, id):
        return klass.get_or_new(connection, (type, id)).count
    
    @classmethod
    def increment(klass, connection, thing=None):
        if thing is None: # increment total
            obj = klass.get_or_new(connection, (klass.TOTAL, 0))
        elif isinstance(thing, Channel):
            obj = klass.get_or_new(connection, (klass.CHANNEL, thing.id))
        elif isinstance(thing, Item):
            obj = klass.get_or_new(connection, (klass.ITEM, thing.id))
        else:
            raise ValueError("Cannot increment: %r" % thing)
        obj.count += 1
        obj.save(connection)
