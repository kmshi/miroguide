from channelguide.guide.models import Channel
from channelguide.testframework import TestCase
from datetime import datetime, timedelta

class ChannelRecommendationsTest(TestCase):

    def setUp(self):
        TestCase.setUp(self)
        self.user = self.make_user('user')
        self.channels = [self.make_channel(self.user, 'A') for i in range(5)]
        ip0 = '0.0.0.0'
        ip1 = '1.1.1.1'
        ip2 = '2.2.2.2'
        self.add_multiple_subscriptions(self.channels[0], ip0, ip1, ip2)
        self.add_multiple_subscriptions(self.channels[1], ip1, ip2)
        self.add_multiple_subscriptions(self.channels[2], ip2)
        self.add_multiple_subscriptions(self.channels[3], ip0)

    def add_multiple_subscriptions(self, channel, *ips):
        """
        Adds multiple subscriptions to the database at one time.
        """
        for ip in ips:
            self.add_subscription(channel, ip)

    def add_subscription(self, channel, ip_address, timestamp=None,
        ignore=False):
        """
        Adds a single subscription to the database.
        """
        oldThrottle = channel._should_throttle_ip_address
        channel._should_throttle_ip_address = lambda *args: False
        try:
            channel.add_subscription(self.connection, ip_address,
                    timestamp=timestamp,
                    ignore_for_recommendations=ignore)
            self.connection.commit()
        finally:
            channel._should_throttle_ip_address = oldThrottle

    def test_get_similarity(self):
        """
        Test that the similarity is calculated as the cosine between the two
        vectors of subscriptions shared by the two channels.
        """
        c0, c1, c2, c3, c4 = self.channels
        # angle of 90 degrees
        self.assertEquals(c0.get_similarity(self.connection, c3.id), 0)
        self.assertEquals(c0.get_similarity(self.connection, c4.id), 0)
        # angle of 45 degrees
        self.assertAlmostEquals(c0.get_similarity(self.connection, c2.id),
                0.70710678, 8)
        self.assertAlmostEquals(c1.get_similarity(self.connection, c2.id),
                0.70710678, 8)
        # angle of 0 degrees
        self.assertAlmostEqual(c0.get_similarity(self.connection, c1.id),
                1, 8)

    def test_ignore_old_recommendations(self):
        """
        Recommendation calculations should ignore subscriptions older than
        6 months (16070400 seconds).
        """
        c1, c2 = self.channels[1:3]
        oldTime = datetime.now() - timedelta(weeks=24, days=5)
        self.add_subscription(c2, "1.1.1.1", oldTime)
        self.assertNotAlmostEqual(c1.get_similarity(self.connection, c2.id),
                1, 8)

    def test_ignore_ignored_recommendations(self):
        """
        Recommendation calculations should ignore recommendations where the
        ignore_for_recommendations field is True.
        """
        c1, c2 = self.channels[1:3]
        self.add_subscription(c2, "1.1.1.1", ignore=True)
        self.assertNotAlmostEqual(c1.get_similarity(self.connection, c2.id),
                1, 8)

