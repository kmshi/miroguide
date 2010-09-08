# Copyright (c) 2009 Participatory Culture Foundation
# See LICENSE for details.

from django.db import models
from channelguide.channels.models import Channel, Item

class WatchedVideosManager(models.Manager):

    def _type_and_id_for(self, thing):
        if thing is None: # toal
            return (self.model.TOTAL, 0)
        elif isinstance(thing, Channel):
            return (self.model.CHANNEL, thing.pk)
        elif isinstance(thing, Item):
            return (self.model.ITEM, thing.pk)
        else:
            raise ValueError("Cannot watch: %r" % thing)

    def count_for(self, thing=None):
        type, id = self._type_and_id_for(thing)
        watcher, created = self.get_or_create(type=type, id=id)
        return watcher.count

    def increment(self, thing=None):
        type, id = self._type_and_id_for(thing)
        watcher, created = self.get_or_create(type=type, id=id,
                                              defaults={'count': 1})
        if not created:
            watcher.count += 1
            watcher.save()

class WatchedVideos(models.Model):
    primary = models.AutoField(primary_key=True)
    type = models.IntegerField()
    id = models.IntegerField()
    count = models.IntegerField(default=0)

    objects = WatchedVideosManager()

    # values for type
    TOTAL = 0
    CHANNEL = 1
    ITEM = 2
