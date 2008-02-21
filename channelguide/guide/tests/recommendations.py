from channelguide.guide.models import Rating
from channelguide.guide import tables
from channelguide.testframework import TestCase
from channelguide import manage
from datetime import datetime, timedelta
import math
from channelguide.guide import recommendations

cos45 = float('%6f' % math.cos(math.radians(45)))

class RecommendationsTestBase(TestCase):
    """
    The item similarities should be:
        0-1: 1
        0-2: 0.5
        0-4: 0.707
        0-6: 0.707
        0-9: 0.707
        1-2: 0.5
        1-4: 0.707
        1-6: 0.707
        1-9: 0.707
        2-8: 0.707
        4-6: 1
        4-9: 1
        6-9: 1
    """
    def setUp(self):
        TestCase.setUp(self)
        self.user = self.make_user('user')
        self.channels = [self.make_channel(self.user, 'A') for i in range(10)]
        self.channels.append(self.make_channel(self.user, 'U'))
        ip0 = '0.0.0.0'
        ip1 = '1.1.1.1'
        ip2 = '2.2.2.2'
        ip3 = '3.3.3.3'
        self.add_multiple_subscriptions(self.channels[0], ip0, ip1, ip2)
        self.add_multiple_subscriptions(self.channels[1], ip1, ip2)
        self.add_multiple_subscriptions(self.channels[2], ip2, ip3)
        self.add_subscription(self.channels[3], ip0)
        self.add_multiple_subscriptions(self.channels[4], ip0, ip1)
        self.add_subscription(self.channels[5], ip1, ignore=True)
        self.add_subscription(self.channels[6], ip1,
            timestamp=datetime.now()-timedelta(days=3))
        self.add_subscription(self.channels[7], ip1,
            timestamp=datetime.now()-timedelta(days=31 * 7))
        self.add_subscription(self.channels[8], ip3)
        self.add_subscription(self.channels[9], ip1,
                timestamp=datetime.now()-timedelta(days=3))
        self.add_multiple_subscriptions(self.channels[10], ip1, ip2)

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
            self.refresh_connection()
            manage.refresh_stats_table()
            self.refresh_connection()

class ChannelRecommendationsTest(RecommendationsTestBase):

    def test_get_similarity(self):
        """
        Test that the similarity is calculated as the cosine between the two
        vectors of subscriptions shared by the two channels.
        """
        c0, c1, c2, c3, c4 = self.channels[:5]
        # angle of 90 degrees
        self.assertEquals(recommendations.get_similarity(c3,
            self.connection, c4.id), 0)
        # angle of 60 degrees
        self.assertAlmostEquals(recommendations.get_similarity(c0,
            self.connection, c2.id), 0.5, 8)
        self.assertAlmostEquals(recommendations.get_similarity(c1,
            self.connection, c2.id), 0.5, 8)
        # angle of 0 degrees
        self.assertAlmostEqual(recommendations.get_similarity(c0,
            self.connection, c1.id), 1, 8)

    def test_ignore_null_ip_address(self):
        """
        get_similarity should not count 0.0.0.0 as a common IP since it is used
        if the IP is not known.
        """
        c0, c3 = self.channels[0], self.channels[3]
        self.assertEquals(recommendations.get_similarity(c0,
            self.connection, c3.id), 0)

    def test_ignore_old_recommendations(self):
        """
        Recommendation calculations should ignore subscriptions older than
        6 months (16070400 seconds).
        """
        c4, c7 = self.channels[4], self.channels[7]
        self.assertEquals(recommendations.get_similarity(c4,
            self.connection, c7.id), 0)

    def test_ignore_ignored_subscription(self):
        """
        Recommendation calculations should ignore recommendations where the
        ignore_for_recommendations field is True.
        """
        c4, c5 = self.channels[4], self.channels[5]
        self.assertEquals(recommendations.get_similarity(c4,
            self.connection, c5.id), 0)

    def get_recommendation_from_database(self, id1, id2, returnOne=True):
        value = self.connection.execute("""
SELECT cosine FROM cg_channel_recommendations
WHERE channel1_id=%s AND channel2_id=%s
""", (id1, id2))
        if returnOne:
            self.assertEquals(len(value), 1)
            return value[0][0]
        else:
            return value

    def insert_recommendations(self):
        """
        Insert some dummy recommendations into the database.
        """
        c0, c1, c2 = self.channels[:3]
        self.connection.execute("DELETE FROM cg_channel_recommendations")
        recommendations.insert_recommendation(c0, self.connection, c1.id)
        recommendations.insert_recommendation(c2, self.connection, c1.id)

    def test_insert_recommendation(self):
        """
        insert_recommendation should add a new row to the recommendations
        table.  It should keep the first channel id lower than the second
        channel id.
        """
        c0, c1, c2 = self.channels[:3]
        self.connection.execute("DELETE FROM cg_channel_recommendations")
        recommendations.insert_recommendation(c0, self.connection, c1.id)
        self.assertAlmostEquals(self.get_recommendation_from_database(c0.id,
            c1.id), 1, 3)
        recommendations.insert_recommendation(c2, self.connection, c1.id)
        self.assertAlmostEquals(self.get_recommendation_from_database(c1.id,
            c2.id), 0.5, 3)

    def test_insert_skips_null(self):
        """
        insert_recommendation should not insert 0 recommendations.
        """
        c2, c4 = self.channels[2], self.channels[4]
        recommendations.insert_recommendation(c2, self.connection, c4.id)
        self.assertEquals(self.get_recommendation_from_database(c2.id, c4.id, False), ())

    def test_delete_old_recommendations(self):
        """
        delete_recommendations should delete the recommendations for the
        channels in the given list for the channel.
        """
        self.insert_recommendations() # add some recommendations
        c0, c1, c2 = self.channels[:3]
        recommendations.insert_recommendation(c0, self.connection, c2.id)
        for other in [c0, c1]:
            recommendations.delete_recommendation(c2, self.connection,
                other.id)
        self.assertEquals(self.connection.execute("""
SELECT * FROM cg_channel_recommendations
WHERE channel1_id=%s OR channel2_id=%s""", (c2.id, c2.id)), ())
        self.assertAlmostEquals(self.get_recommendation_from_database(c0.id, c1.id), 1, 3)

    def test_find_relevant_similar(self):
        """
        find_relevant_similar when given an IP address should return the other
        channels that the ip_address has subscribed to.  It should not include
        channels that are not accepted. or ignored subscriptions.
        """
        c0, c1 = self.channels[:2]
        c4, c6, c9 = self.channels[4], self.channels[6], self.channels[9]
        self.assertEquals(recommendations.find_relevant_similar(c1,
            self.connection, '1.1.1.1'), [c0.id, c4.id, c6.id, c9.id])

    def test_find_relevant_similar_no_ip(self):
        """
        find_relevant_similar without an IP should return all the channels that
        share a subscription with the given channel.  It should not include
        0.0.0.0 as a common ip, ignored subscriptions, or non-approved
        channels.
        """
        c0, c1, c2 = self.channels[:3]
        c4, c6, c8 = self.channels[4], self.channels[6], self.channels[8]
        c9 = self.channels[9]
        self.assertEquals(recommendations.find_relevant_similar(c1,
            self.connection), [c0.id, c2.id, c4.id, c6.id, c9.id])
        self.assertEquals(recommendations.find_relevant_similar(c2,
            self.connection), [c0.id, c1.id, c8.id])
        self.assertEquals(recommendations.find_relevant_similar(c4,
            self.connection), [c0.id, c1.id, c6.id, c9.id])

    def test_full_calculation(self):
        """
        manange.calculateAllRecommendations() should populate the
        recommendations table with all recommendations for all
        channels.
        """
        c0, c1, c2, c3, c4, c5, c6, c7, c8, c9 = self.channels[:10]
        calculate = manage.action_mapping['calculate_recommendations']
        calculate(['manage.py', 'calculate_recommendations', 'full'])
        rows = sorted(tables.channel_recommendations.select('*').execute(self.connection))
        check = sorted(((c0.id, c1.id, 1),
                (c0.id, c2.id, 0.5),
                (c0.id, c4.id, cos45),
                (c0.id, c6.id, cos45),
                (c0.id, c9.id, cos45),
                (c1.id, c2.id, 0.5),
                (c1.id, c4.id, cos45),
                (c1.id, c6.id, cos45),
                (c1.id, c9.id, cos45),
                (c2.id, c8.id, cos45),
                (c4.id, c6.id, 1),
                (c4.id, c9.id, 1),
                (c6.id, c9.id, 1),
                ))
        self.assertEquals(rows, check)

    def test_partial_calculation(self):
        """
        manage.calculateTwoDaysRecommendations() should update the
        recommendations table with recommendations for channels that have
        had a subscription the past 2 days.
        """
        c0, c1, c2, c3, c4, c5, c6, c7, c8, c9 = self.channels[:10]
        calculate = manage.action_mapping['calculate_recommendations']
        calculate(['manage.py', 'calculate_recommendations'])
        rows = sorted(tables.channel_recommendations.select('*').execute(self.connection))
        cos45 = float('%6f' % math.cos(math.radians(45)))
        check = sorted(((c0.id, c1.id, 1),
                (c0.id, c2.id, 0.5),
                (c0.id, c4.id, cos45),
                (c0.id, c6.id, cos45),
                (c0.id, c9.id, cos45),
                (c1.id, c2.id, 0.5),
                (c1.id, c4.id, cos45),
                (c1.id, c6.id, cos45),
                (c1.id, c9.id, cos45),
                (c2.id, c8.id, cos45),
                (c4.id, c6.id, 1),
                (c4.id, c9.id, 1),
                ))
        self.assertEquals(rows, check)

class PersonalizedRecommendationsTest(RecommendationsTestBase):

    def setUp(self):
        RecommendationsTestBase.setUp(self)
        recommendations.recalculate_recently_subscribed(self.connection)

    def test_calculate_scores(self):
        ratings = {
                self.channels[0].id: 5,
                self.channels[4].id: 3,
            }
        recommendations = self.user._get_recommendations(self.connection,
               ratings.keys())
        scores, numScores, topThree = self.user._calculate_scores(
                recommendations, ratings)
        self.assertEquals(scores, {
                    self.channels[1].id: (5 + (3 * cos45)) / (1 + cos45),
                    self.channels[2].id: 5,
                    self.channels[6].id: (3 + (5 * cos45)) / (1 + cos45),
                    self.channels[9].id: (3 + (5 * cos45)) / (1 + cos45)})
        self.assertEquals(numScores, {
                    self.channels[1].id: 2,
                    self.channels[2].id: 1,
                    self.channels[6].id: 2,
                    self.channels[9].id: 2})
        self.assertEquals(topThree, {
            self.channels[1].id:
                [(3 * cos45, self.channels[4].id), (5, self.channels[0].id)],
            self.channels[2].id:
                [(0.5 * 5, self.channels[0].id)],
            self.channels[6].id:
                [(3, self.channels[4].id), (5 * cos45, self.channels[0].id)],
            self.channels[9].id:
                [(3, self.channels[4].id), (5 * cos45, self.channels[0].id)],
            })
