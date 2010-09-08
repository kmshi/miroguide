# Copyright (c) 2008-2009 Participatory Culture Foundation
# See LICENSE for details.

from datetime import datetime, timedelta

from django.conf import settings
from django.core import management
from django.core.urlresolvers import reverse

from channelguide.subscriptions.models import Subscription
from channelguide.subscriptions.views import subscribe_hit
from channelguide.testframework import TestCase

class SubscriptionTestCase(TestCase):
    """Test operations on the Channel class."""

    def setUp(self):
        TestCase.setUp(self)
        self.ralph = self.make_user('ralph')
        self.channel = self.make_channel(self.ralph)

    def check_subscription_counts(self, total, month, today, use_cache=False):
        subscription_count = Subscription.objects.total(
            self.channel,
            use_cache=use_cache)
        subscription_count_month = Subscription.objects.total(
            self.channel,
            size='month',
            use_cache=use_cache)
        subscription_count_today = Subscription.objects.total(
            self.channel,
            size='day',
            use_cache=use_cache)
        self.assertEquals(subscription_count, total)
        self.assertEquals(subscription_count_month, month)
        self.assertEquals(subscription_count_today, today)

    def test_subscription_counts(self):
        now = datetime.now()
        week = timedelta(days=7)

        self.check_subscription_counts(0, 0, 0)
        Subscription.objects.add(self.channel, '1.1.1.1', now)
        self.check_subscription_counts(1, 1, 1)
        Subscription.objects.add(self.channel, '1.1.1.1', now-week)
        self.check_subscription_counts(2, 2, 1)
        Subscription.objects.add(self.channel, '1.1.1.1', now-week*6)
        self.check_subscription_counts(3, 2, 1)

    def test_subscription_spam_prevention(self):
        next_week = datetime.now() + timedelta(days=7)
        Subscription.objects.add(self.channel, '1.1.1.1')
        self.check_subscription_counts(1, 1, 1)
        Subscription.objects.add(self.channel, '1.1.1.1')
        self.check_subscription_counts(1, 1, 1)
        Subscription.objects.add(self.channel, '1.1.1.1', next_week)
        self.check_subscription_counts(2, 2, 2)

    def test_stats_refresh(self):
        """
        Test that manage.refresh_stats_table() correctly updates the
        subscription table.
        """
        now = datetime.now()
        week = timedelta(days=7)
        self.channel.state = 'A'
        self.channel.save()
        self.check_subscription_counts(0, 0, 0)
        Subscription.objects.add(self.channel, '1.1.1.1', now-week)
        Subscription.objects.add(self.channel, '1.1.1.1', now-week*6)
        Subscription.objects.add(self.channel, '1.1.1.1', now)
        self.check_subscription_counts(0, 0, 0, use_cache=True)
        management.call_command('refresh_stats_table', verbosity=0)
        self.check_subscription_counts(3, 2, 1, use_cache=True)

    def test_subscription_view(self):
        url = reverse(subscribe_hit, args=(self.channel.pk,))
        self.get_page(url)
        self.check_subscription_counts(1, 1, 1)

    def test_ignore_for_recommendation_from_other_channel(self):
        url = reverse(subscribe_hit, args=(self.channel.pk,))
        other_channel = reverse('channelguide.channels.views.channel',
                                args=(self.channel.pk+1,))
        self.client.get(url,
                        HTTP_REFERER=settings.BASE_URL_FULL+other_channel)
        sub = Subscription.objects.get(channel=self.channel)
        self.assertEquals(sub.ignore_for_recommendations, True)

    def test_ignore_for_recommendation_from_firsttime(self):
        url = reverse(subscribe_hit, args=(self.channel.pk,))
        other_channel = reverse('channelguide.guide.views.firsttime.index')
        self.client.get(url,
                        HTTP_REFERER=settings.BASE_URL_FULL+other_channel)
        sub = Subscription.objects.get(channel=self.channel)
        self.assertEquals(sub.ignore_for_recommendations, True)
