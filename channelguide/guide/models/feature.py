# Copyright (c) 2008-2009 Participatory Culture Foundation
# See LICENSE for details.

import datetime

from django.conf import settings

from channelguide.guide import tables
from sqlhelper.orm import Record
from sqlhelper.exceptions import NotFoundError

class FeaturedQueue(Record):
    table = tables.featured_queue

    IN_QUEUE = 0
    CURRENT = 1
    PAST = 2

    @classmethod
    def featured(cls, state=None, channel_state=None):
        if state == None:
            state = cls.CURRENT
        query = cls.query().where(cls.c.state==state).order_by(
            cls.c.featured_at, desc=True).join('channel')
        channel_join = query.joins['channel']
        if channel_state is None:
            channel_state = 'A'
        channel_join.where(channel_join.c.state == channel_state)
        return query

    @classmethod
    def users_in_queue(cls, connection, channel_state):
        query = cls.featured(cls.IN_QUEUE, channel_state)
        return set(fq.featured_by_id for fq in query.execute(connection))

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
            channel.change_featured(None, connection)
            fq.state = cls.PAST
            fq.save(connection)
            cls.shuffle_queue(connection)

    @classmethod
    def shuffle_queue(cls, connection, channel_state=None):
        count = cls.featured(channel_state=channel_state).count(connection)
        while count >= settings.MAX_FEATURES:
            query = cls.featured(channel_state=channel_state).order_by(
                None).order_by(cls.c.featured_at).limit(1)
            old = query.get(connection)
            old.channel.change_featured(None, connection)
            old.state = cls.PAST
            old.save(connection)
            count -= 1
        for i in range(count, settings.MAX_FEATURES):
            fq = cls.get_next_feature(connection, channel_state=channel_state)
            if fq is None:
                return
            fq.join('featured_by').execute(connection)
            fq.state = cls.CURRENT
            fq.featured_at = datetime.datetime.now()
            fq.channel.change_featured(fq.featured_by, connection)
            fq.save(connection)

    @classmethod
    def get_next_feature(cls, connection, channel_state=None):
        if channel_state is None:
            channel_state = 'A'
        valid_user_ids = cls.users_in_queue(connection, channel_state)
        if not valid_user_ids:
            return None
        query = cls.query().load('last_time').join('channel')
        query.joins['channel'].where(
            query.joins['channel'].c.state == channel_state)
        query.where(cls.c.featured_by_id.in_(valid_user_ids))
        query.group_by(cls.c.featured_by_id)
        query.order_by('last_time').order_by('featured_at').limit(1)
        try:
            last_user_id = query.get(connection).featured_by_id
        except NotFoundError:
            return None
        return cls.featured(cls.IN_QUEUE, channel_state).where(
            cls.c.featured_by_id == last_user_id).order_by(
            None).order_by(cls.c.featured_at).limit(1).execute(connection)[0]
