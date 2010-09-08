# Copyright (c) 2009 Participatory Culture Foundation
# See LICENSE for details.

from django.db import models

class Flag(models.Model):
    channel = models.ForeignKey('channels.Channel', db_index=True,
                                related_name='flags')
    user = models.ForeignKey('auth.User', db_index=True, null=True)
    flag = models.IntegerField()

    class Meta:
        db_table = 'cg_channel_flags'
        unique_together = [('channel', 'user', 'flag')]

    NOT_HD = 0
