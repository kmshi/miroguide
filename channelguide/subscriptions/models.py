from datetime import datetime, timedelta

from django.db import models
from django.core import cache

class SubscriptionManager(models.Manager):

    def _should_throttle_ip_address(self, ip_address, timestamp):
        """Check to see if we got a subscription from the same ip address too
        recently.
        """
        second_ago = timestamp - timedelta(seconds=1)
        return bool(
            self.filter(ip_address=ip_address,
                        timestamp__gt=second_ago).count())

    def add(self, channel, ip_address, timestamp=None,
            ignore_for_recommendations=False):
        if timestamp is None:
            timestamp = datetime.now()
            if self._should_throttle_ip_address(ip_address, timestamp):
                return
        self.create(
            channel=channel,
            ip_address=ip_address,
            timestamp=timestamp,
            ignore_for_recommendations=ignore_for_recommendations)

    def total(self, channel, size=None, use_cache=True):
        key = 'subscription:%i:%s' % (channel.pk, size)
        if use_cache:
            val = cache.cache.get(key)
            if val is not None:
                return val
        if size is None:
            val = self.filter(channel=channel).count()
        else:
            if size == 'month':
                delta = timedelta(days=31)
            elif size == 'day':
                delta = timedelta(days=1)
            else:
                raise ValueError('invalid size: %r' % size)
            val = self.filter(channel=channel,
                            timestamp__gt=(datetime.now() - delta)).count()
        cache.cache.set(key, val, 600) # statistics are good for 10 minutes
        return val

class Subscription(models.Model):
    channel = models.ForeignKey('channels.Channel')
    ip_address = models.IPAddressField()
    timestamp = models.DateTimeField()
    ignore_for_recommendations = models.BooleanField()

    objects = SubscriptionManager()

    class Meta:
        db_table = 'cg_channel_subscription'


class GeneratedStats(models.Model):
    channel = models.OneToOneField('channels.Channel', primary_key=True,
                                   related_name='stats')
    subscription_count_today = models.IntegerField(default=0)
    subscription_count_month = models.IntegerField(default=0)
    subscription_count = models.IntegerField(default=0,
        db_column='subscription_count_total')

    class Meta:
        db_table = 'cg_channel_generated_stats'

    def rank(self, column):
        kw = {'%s__gte' % column: getattr(self, column)}
        return '%i/%i' % (GeneratedStats.objects.filter(**kw).count(),
                          GeneratedStats.objects.count())

    @property
    def subscription_count_today_rank(self):
        return self.rank('subscription_count_today')

    @property
    def subscription_count_month_rank(self):
        return self.rank('subscription_count_month')

    @property
    def subscription_count_rank(self):
        return self.rank('subscription_count')
