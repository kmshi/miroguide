# Copyright (c) 2009 Participatory Culture Foundation
# See LICENSE for details.

from datetime import datetime

from channelguide.testframework import TestCase
from channelguide.channels.models import Item
from channelguide.watched.models import WatchedVideos

class WatchedVideosTestCase(TestCase):

    def setUp(self):
        TestCase.setUp(self)
        self.owner = self.make_user('owner')
        self.channel = self.make_channel(self.owner)
        self.item = Item.objects.create(
            channel=self.channel,
            name="Item",
            description=self.channel.description,
            url=self.channel.url + '/item',
            size=0,
            date=datetime.now())

    def assertCounts(self, total, channel, item):
        self.assertEquals(WatchedVideos.objects.count_for(),
                          total)
        self.assertEquals(WatchedVideos.objects.count_for(self.channel),
                          channel)
        self.assertEquals(WatchedVideos.objects.count_for(self.item),
                          item)

    def test_default(self):
        self.assertCounts(0, 0, 0)

    def test_increment_total(self):
        WatchedVideos.objects.increment()
        self.assertCounts(1, 0, 0)

    def test_increment_channel(self):
        WatchedVideos.objects.increment(self.channel)
        self.assertCounts(0, 1, 0)

    def test_increment_item(self):
        WatchedVideos.objects.increment(self.item)
        self.assertCounts(0, 0, 1)

    def test_view_increments_all_three(self):
        self.post_data('/ping/watched',
                       {'feed': self.channel.url,
                       'item': self.item.url})
        self.assertCounts(1, 1, 1)

    def test_view_increments_only_channel(self):
        self.post_data('/ping/watched',
                       {'feed': self.channel.url})
        self.assertCounts(1, 1, 0)

    def test_view_increments_only_total(self):
        self.post_data('/ping/watched', {})
        self.assertCounts(1, 0, 0)

    def test_view_guesses_channel_from_item(self):
        self.post_data('/ping/watched', {
            'item': self.item.url})
        self.assertCounts(1, 1, 1)
