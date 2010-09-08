# Copyright (c) 2008-2009 Participatory Culture Foundation
# See LICENSE for details.

from django.db import models

class ModeratorAction(models.Model):
    user = models.ForeignKey('auth.User', related_name='moderator_actions')
    channel = models.ForeignKey('channels.Channel',
                                related_name='moderator_actions')
    action = models.CharField(max_length=1)
    timestamp = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'cg_moderator_action'
        ordering = ['-id']

    def get_action_name(self):
        return self.channel.name_for_state_code[self.action]
    action_name = property(get_action_name)
