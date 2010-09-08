# Copyright (c) 2008-2009 Participatory Culture Foundation
# See LICENSE for details.

from django.db import models

class Rating(models.Model):
    channel = models.ForeignKey('channels.Channel', db_index=True,
                                related_name='user_ratings')
    user = models.ForeignKey('auth.User', db_index=True,
                             related_name='ratings')
    rating = models.IntegerField(null=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'cg_channel_rating'
        unique_together = [('channel', 'user')]

    def __unicode__(self):
        return u'<Rating of %s by %s: %s>' % (self.channel, self.user,
                                              self.rating)

class GeneratedRatings(models.Model):
    channel = models.OneToOneField('channels.Channel', primary_key=True,
                                   related_name='rating')
    average = models.FloatField(default=0.0)
    count = models.IntegerField(default=0)
    total = models.IntegerField(default=0)

    class Meta:
        db_table = 'cg_channel_generated_ratings'

from django.db.models import signals
from channelguide.user_profile.models import UserProfile

def pre_rating_save(instance=None, **kwargs):
    try:
        previous = Rating.objects.get(channel=instance.channel,
                                      user=instance.user)
    except Rating.DoesNotExist:
        return
    gr, created = GeneratedRatings.objects.get_or_create(
        channel=instance.channel)
    if previous.rating is not None and previous.user.get_profile().approved:
        gr.count -= 1
        gr.total -= previous.rating
        if gr.count:
            gr.average = float(gr.total) / gr.count
        else:
            gr.total = gr.average = 0
        gr.save()

def post_rating_save(instance=None, **kwargs):
    gr, created = GeneratedRatings.objects.get_or_create(
        channel=instance.channel)
    if instance.rating is not None and instance.user.get_profile().approved:
        gr.count += 1
        gr.total += instance.rating
        gr.average = float(gr.total) / gr.count
    gr.save()


def pre_user_profile_save(instance=None, **kwargs):
    try:
        UserProfile.objects.get(pk=instance.pk)
    except UserProfile.DoesNotExist:
        return
    if instance.approved:
        for rating in instance.user.ratings.all():
            rating.user = instance.user
            pre_rating_save(instance=rating)
            post_rating_save(instance=rating)

signals.pre_save.connect(pre_rating_save, sender=Rating)
signals.post_save.connect(post_rating_save, sender=Rating)
signals.pre_save.connect(pre_user_profile_save, sender=UserProfile)
