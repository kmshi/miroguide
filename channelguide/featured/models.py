# Copyright (c) 2008-2009 Participatory Culture Foundation
# See LICENSE for details.

import datetime

from django.conf import settings
from django.db import models

from channelguide.channels.models import Channel

class FeaturedQueueManager(models.Manager):

    def users_in_queue(self, channel_state):
        return self.filter(state=self.model.IN_QUEUE,
                           channel__state=channel_state).values_list(
            'featured_by', flat=True).distinct()

    def feature(self, channel, user):
        self.filter(channel=channel).delete()
        fq = self.model(channel=channel,
                 state=self.model.IN_QUEUE,
                 featured_by=user)
        fq.save()
        return fq

    def unfeature(self, channel, do_shuffle=True):
        fq = self.get(channel=channel)
        if fq.state == self.model.IN_QUEUE:
            fq.delete()
        elif fq.state == self.model.CURRENT:
            channel.change_featured(None)
            fq.state = self.model.PAST
            fq.save()
            if do_shuffle:
                self.shuffle(channel_state=channel.state)

    def shuffle(self, channel_state=Channel.APPROVED):
        count = self.filter(state=self.model.CURRENT,
                            channel__state=channel_state).count()
        while count >= settings.MAX_FEATURES:
            last = self.filter(state=self.model.CURRENT,
                               channel__state=channel_state).order_by(
                'featured_at')[0]
            self.unfeature(last.channel, do_shuffle=False)
            count -= 1
        for i in range(count, settings.MAX_FEATURES):
            fq = self._get_next_feature(channel_state)
            if fq is None:
                return
            fq.state = self.model.CURRENT
            fq.featured_at = datetime.datetime.now()
            fq.channel.change_featured(fq.featured_by)
            fq.save()

    def _with_last_time(self):
        return self.extra(
            select={
                'last_time': "COALESCE("
                "(SELECT featured_at from cg_channel_featured_queue AS q2 "
                "WHERE q2.state!=%s AND "
                "q2.featured_by_id=cg_channel_featured_queue.featured_by_id "
                "ORDER BY q2.featured_at DESC LIMIT 1), 0)"},
            select_params=[self.model.IN_QUEUE]).extra(
            order_by=['last_time'])


    def _get_next_feature(self, channel_state):
        users_in_queue = self.users_in_queue(channel_state)
        if not users_in_queue:
            return
        last_user = self._with_last_time().filter(
            state=self.model.IN_QUEUE,
            channel__state=channel_state)[0].featured_by
        return self.filter(state=self.model.IN_QUEUE,
                           featured_by=last_user).order_by(
            ).order_by('featured_at')[0]

class FeaturedQueue(models.Model):
    channel = models.OneToOneField('channels.Channel', primary_key=True,
                                   related_name='featured_queue')
    state = models.IntegerField(default=0)
    featured_by = models.ForeignKey('auth.User')
    featured_at = models.DateTimeField(auto_now_add=True)

    objects = FeaturedQueueManager()

    class Meta:
        db_table = 'cg_channel_featured_queue'
        ordering = ['-featured_at']

    IN_QUEUE = 0
    CURRENT = 1
    PAST = 2

class FeaturedEmail(models.Model):
    sender = models.ForeignKey('auth.User')
    channel = models.ForeignKey('channels.Channel',
                                related_name='featured_emails')
    email = models.EmailField(max_length=100)
    title = models.CharField(max_length=100)
    body = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)


    class Meta:
        db_table = 'cg_channel_featured_email'
        ordering = ['-id']
