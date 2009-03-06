from sqlhelper.orm import Record
from channelguide.guide import tables

class Flag(Record):
    table = tables.flags

    NOT_HD = 0

    def __init__(self, channel, user, flag):
        self.channel_id = channel.id
        if user is not None and user.is_authenticated():
            self.user_id = user.id
        else:
            self.user_id = None
        self.flag = flag

    @classmethod
    def count(cls, connection, flag):
        q = cls.query()
        q.where(cls.c.flag == flag)
        q.group_by(cls.c.channel_id)
        return len(q.execute(connection))
