from channelguide.testframework import TestCase
from channelguide.guide.models import WatchedVideos, Item

class WatchedVideosTestCase(TestCase):

    def setUp(self):
        TestCase.setUp(self)
        self.owner = self.make_user('owner')
        self.channel = self.make_channel(self.owner)
        self.item = Item()
        self.item.channel_id = self.channel.id
        self.item.name = "Item"
        self.item.description = self.channel.description
        self.item.url = self.channel.url + '/item'
        self.item.save(self.connection)
        self.refresh_connection()

    def assertCounts(self, total, channel, item):
        self.assertEquals(WatchedVideos.count(self.connection,
                                              WatchedVideos.TOTAL, 0),
                          total)
        self.assertEquals(WatchedVideos.count(self.connection,
                                              WatchedVideos.CHANNEL,
                                              self.channel.id),
                          channel)
        self.assertEquals(WatchedVideos.count(self.connection,
                                              WatchedVideos.ITEM,
                                              self.item.id),
                          item)

    def test_default(self):
        self.assertCounts(0, 0, 0)

    def test_increment_total(self):
        WatchedVideos.increment(self.connection)
        self.assertCounts(1, 0, 0)

    def test_increment_channel(self):
        WatchedVideos.increment(self.connection, self.channel)
        self.assertCounts(0, 1, 0)

    def test_increment_item(self):
        WatchedVideos.increment(self.connection, self.item)
        self.assertCounts(0, 0, 1)

    def test_view_increments_all_three(self):
        self.post_data('/ping/watched',
                       {'feed': self.channel.url,
                       'item': self.item.url})
        self.refresh_connection()
        self.assertCounts(1, 1, 1)

    def test_view_increments_only_channel(self):
        self.post_data('/ping/watched',
                       {'feed': self.channel.url})
        self.refresh_connection()
        self.assertCounts(1, 1, 0)

    def test_view_increments_only_total(self):
        self.post_data('/ping/watched', {})
        self.refresh_connection()
        self.assertCounts(1, 0, 0)

    def test_view_guesses_channel_from_item(self):
        self.post_data('/ping/watched', {
            'item': self.item.url})
        self.refresh_connection()
        self.assertCounts(1, 1, 1)
