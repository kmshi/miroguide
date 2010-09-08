from django.core.management.base import BaseCommand

from channelguide.subscriptions.models import Subscription, GeneratedStats
from channelguide.channels.models import Channel

class Command(BaseCommand):

    def handle(self, **kwargs):
        """
        Refreshes the statistics table so that we can calculate the ranks of
        channels.
        """
        for channel in Channel.objects.approved():
            sizes = {}
            for size in None, 'month', 'day':
                sizes[size] = Subscription.objects.total(channel, size,
                                                         use_cache=False)
            generated_stat, created = GeneratedStats.objects.get_or_create(
                channel=channel)
            generated_stat.subscription_count_today = sizes['day']
            generated_stat.subscription_count_month = sizes['month']
            generated_stat.subscription_count = sizes[None]
            generated_stat.save()

