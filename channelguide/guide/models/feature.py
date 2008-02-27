# Copyright (c) 2008 Participatory Culture Foundation
# See LICENSE for details.

import datetime

from django.conf import settings

from channelguide.guide import tables
from sqlhelper.orm import Record

class FeaturedQueue(Record):
    table = tables.featured_queue

    IN_QUEUE = 0
    CURRENT = 1
    PAST = 2

    @classmethod
    def featured(cls, state=None):
        if state == None:
            state = cls.CURRENT
        return cls.query().where(cls.c.state==state).order_by(cls.c.featured_at,desc=True)

    @classmethod
    def users_in_queue(cls):
        query = cls.featured(cls.IN_QUEUE)
        select = query.make_select()
        select.columns = [cls.c.featured_by_id]
        return select

    @classmethod
    def feature_channel(cls, channel, user, connection):
        old = cls.query().where(cls.c.channel_id==channel.id).execute(connection)
        for fq in old:
            fq.delete(connection)
        fq = cls()
        fq.channel_id = channel.id
        fq.state = cls.IN_QUEUE
        fq.featured_by_id = user.id
        fq.save(connection)
        return fq

    @classmethod
    def unfeature_channel(cls, channel, connection):
        fq = cls.get(connection, channel.id)
        if fq.state == cls.IN_QUEUE:
            fq.delete(connection)
        elif fq.state == cls.CURRENT:
            fq.state = cls.PAST
            fq.save(connection)
            cls.shuffle_queue(connection)

    @classmethod
    def shuffle_queue(cls, connection):
        count = cls.featured().count(connection)
        while count >= settings.MAX_FEATURES:
            query = cls.featured().order_by(None).order_by(cls.c.featured_at).limit(1)
            old = query.join('channel').get(connection)
            old.channel.change_featured(None, connection)
            old.state = cls.PAST
            old.save(connection)
            count -= 1
        for i in range(count, settings.MAX_FEATURES):
            fq = cls.get_next_feature(connection)
            fq.join('channel', 'featured_by').execute(connection)
            fq.state = cls.CURRENT
            fq.featured_at = datetime.datetime.now()
            fq.channel.change_featured(fq.featured_by, connection)
            fq.save(connection)

    @classmethod
    def get_next_feature(cls, connection):
        last_user = cls.query().load('last_time').where(
                cls.c.featured_by_id.in_(cls.users_in_queue())).group_by(
                    cls.c.featured_by_id).order_by(
                            'last_time').limit(1).execute(
                                    connection)[0].featured_by_id
        return cls.query().where(cls.c.state==cls.IN_QUEUE,
                cls.c.featured_by_id==last_user).order_by(
                        cls.c.featured_at).limit(1).execute(connection)[0]
