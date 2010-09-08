
# Copyright (c) 2008-2009 Participatory Culture Foundation
# See LICENSE for details.

from datetime import datetime, timedelta
import math

from django.core.management import call_command

from channelguide.ratings.models import Rating
from channelguide.subscriptions.models import Subscription
from channelguide.recommendations.models import Similarity
from channelguide.testframework import TestCase
from channelguide.recommendations import utils

cos45 = float('%6f' % math.cos(math.radians(45)))

class RecommendationsTestBase(TestCase):
    """
    The item similarities for subscriptions should be:
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
        self.users = [self.make_user('user%i' % i) for i in range(5)]
        self.channels = [self.make_channel(self.users[0], 'A')
                for i in range(10)]
        self.channels.append(self.make_channel(self.users[0], 'U'))

        # subscriptions
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

        # ratings
        self.add_ratings(0, 1, 1, 3, 4, 5)
        self.add_ratings(1, 2, 2, 5, 4, 3)
        self.add_ratings(2, 5, 5, 3, 4)
        self.add_ratings(3, 4, 4, 5, 1, 2)
        self.add_ratings(4, 3, 3, 5, 2, 1)

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
        if timestamp is None:
            timestamp = datetime.now()
        Subscription.objects.create(
            channel=channel,
            ip_address=ip_address,
            timestamp=timestamp,
            ignore_for_recommendations=ignore)

    def add_ratings(self, user_index, *ratings):
        user = self.users[user_index]
        for score, channel in zip(ratings, self.channels):
            Rating.objects.create(
                channel=channel,
                user=user,
                rating=score)


class ChannelRecommendationsTest(RecommendationsTestBase):

    def test_get_similarity_from_subscriptions(self):
        """
        Test that the similarity is calculated as the cosine between the two
        vectors of subscriptions shared by the two channels.
        """
        c0, c1, c2, c3, c4 = self.channels[:5]

        c0_c1 = utils.get_similarity_from_subscriptions(
            c0, c1) # 1
        c0_c2 = utils.get_similarity_from_subscriptions(
            c0, c2) # 0.5
        c1_c2 = utils.get_similarity_from_subscriptions(
            c1, c2) # 0.5
        c3_c4 = utils.get_similarity_from_subscriptions(
            c3, c4) # 0
        self.assertTrue(c0_c1 > c0_c2)
        self.assertTrue(c0_c1 > c1_c2)
        self.assertTrue(c0_c1 > c3_c4)
        self.assertTrue(c0_c2 > c3_c4)

    def test_get_similarity_from_ratings(self):
       c0, c1, c2, c3, c4 = self.channels[:5]
       c0_c1 = utils.get_similarity_from_ratings(
           c0, c1.id)
       c0_c2 = utils.get_similarity_from_ratings(
           c0, c2.id)
       c0_c3 = utils.get_similarity_from_ratings(
           c0, c3.id)
       c0_c4 = utils.get_similarity_from_ratings(
           c0, c4.id)
       c1_c2 = utils.get_similarity_from_ratings(
           c1, c2.id)
       c1_c3 = utils.get_similarity_from_ratings(
           c1, c3.id)
       c1_c4 = utils.get_similarity_from_ratings(
           c1, c4.id)
       c2_c3 = utils.get_similarity_from_ratings(
           c2, c3.id)
       c2_c4 = utils.get_similarity_from_ratings(
           c2, c4.id)
       c3_c4 = utils.get_similarity_from_ratings(
           c3, c4.id)
       self.assertTrue(c0_c1 > c0_c2)
       self.assertTrue(c0_c1 > c0_c3)
       self.assertTrue(c0_c1 > c0_c4)
       self.assertTrue(c0_c1 > c1_c2)
       self.assertTrue(c0_c1 > c1_c3)
       self.assertTrue(c0_c1 > c1_c4)
       self.assertTrue(c0_c1 > c2_c3)
       self.assertTrue(c0_c1 > c2_c4)
       self.assertTrue(c0_c1 > c3_c4)
       self.assertTrue(c0_c2 > c0_c3)
       self.assertTrue(c0_c2 > c0_c4)
       self.assertTrue(c0_c2 > c1_c3)
       self.assertTrue(c0_c2 > c1_c4)
       self.assertTrue(c0_c2 > c2_c3)
       self.assertTrue(c0_c3 > c0_c4)
       self.assertTrue(c0_c3 > c1_c4)
       self.assertTrue(c0_c3 > c2_c3)
       self.assertTrue(c0_c3 > c2_c4)
       self.assertTrue(c0_c4 > c2_c4)
       self.assertTrue(c1_c2 > c1_c4)
       self.assertTrue(c1_c2 > c0_c3)
       self.assertTrue(c1_c2 > c0_c4)
       self.assertTrue(c1_c2 > c1_c3)
       self.assertTrue(c1_c2 > c1_c4)
       self.assertTrue(c1_c2 > c2_c3)

    def test_ignore_null_ip_address(self):
        """
        get_similarity_from_subscriptions should not count 0.0.0.0 as a common
        IP since it is used if the IP is not known.
        """
        c0, c3 = self.channels[0], self.channels[3]
        self.assertEquals(utils.get_similarity_from_subscriptions(c0,
            c3.id), 0)

    def test_ignore_old_recommendations(self):
        """
        Recommendation calculations should ignore subscriptions older than
        6 months (16070400 seconds).
        """
        c4, c7 = self.channels[4], self.channels[7]
        self.assertEquals(utils.get_similarity_from_subscriptions(c4,
            c7.id), 0)

    def test_ignore_ignored_subscription(self):
        """
        Recommendation calculations should ignore recommendations where the
        ignore_for_recommendations field is True.
        """
        c4, c5 = self.channels[4], self.channels[5]
        self.assertEquals(utils.get_similarity_from_subscriptions(c4,
            c5.id), 0)

    def get_recommendation_from_database(self, channel1, channel2,
                                         returnOne=True):
        if returnOne:
            method = Similarity.objects.get
        else:
            method = Similarity.objects.filter

        return method(channel1=channel1,
                      channel2=channel2)

    def insert_recommendations(self):
        """
        Insert some dummy recommendations into the database.
        """
        c0, c1, c2 = self.channels[:3]
        Similarity.objects.all().delete()
        Similarity.objects.calculate(c0, c1)
        Similarity.objects.calculate(c1, c2)

    def test_insert_similarity(self):
        """
        insert_similarity should add a new row to the recommendations
        table.  It should keep the first channel id lower than the second
        channel id.
        """
        c0, c1, c2 = self.channels[:3]
        Similarity.objects.calculate(c0, c1)
        self.assertTrue(self.get_recommendation_from_database(c0, c1))
        Similarity.objects.calculate(c2, c1)
        self.assertTrue(self.get_recommendation_from_database(c1, c2))

    def test_find_relevant_similar_subscription(self):
        """
        find_relevant_similar when given an IP address should return the other
        channels that the ip_address has subscribed to.  It should not include
        channels that are not accepted. or ignored subscriptions.
        """
        c0, c1 = self.channels[:2]
        c4, c6, c9 = self.channels[4], self.channels[6], self.channels[9]
        self.assertSameSet(
            utils.find_relevant_similar_subscription(c1, '1.1.1.1'),
            [c0.id, c4.id, c6.id, c9.id])

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
        self.assertSameSet(utils.find_relevant_similar_subscription(c1),
                          [c0.id, c2.id, c4.id, c6.id, c9.id])
        self.assertSameSet(utils.find_relevant_similar_subscription(c2),
                          [c0.id, c1.id, c8.id])
        self.assertSameSet(utils.find_relevant_similar_subscription(c4),
                          [c0.id, c1.id, c6.id, c9.id])

    def test_find_relevant_similar_rating(self):
        c0, c1, c2, c3, c4 = self.channels[:5]
        self.assertSameSet(utils.find_relevant_similar_rating(c0),
                           [c1.id, c2.id, c3.id, c4.id])

    def test_calculation(self):
        """
        manage.calculate_recommendations should update the
        recommendations table.
        """
        c0, c1, c2, c3, c4 = self.channels[:5]
        call_command('calculate_recommendations')
        rows = sorted(Similarity.objects.values_list('channel1', 'channel2'))
        check = sorted(((c0.id, c1.id),
                        (c0.id, c2.id),
                        (c0.id, c3.id),
                        (c0.id, c4.id),
                        (c1.id, c2.id),
                        (c1.id, c3.id),
                        (c1.id, c4.id),
                        (c2.id, c3.id),
                        (c2.id, c4.id),
                        (c3.id, c4.id),
                        ))
        self.assertEquals(rows, check)

class PersonalizedRecommendationsTest(RecommendationsTestBase):

    def setUp(self):
        RecommendationsTestBase.setUp(self)
        rows = (
                (self.channels[0].id, self.channels[1].id, 0.5),
                (self.channels[0].id, self.channels[2].id, -0.5),
                (self.channels[0].id, self.channels[3].id, 0.6),
                (self.channels[1].id, self.channels[4].id, -0.1),
                (self.channels[2].id, self.channels[4].id, 0.9),
                (self.channels[3].id, self.channels[4].id, 0.2),
            )
        for row in rows:
            Similarity.objects.create(
                channel1_id=row[0],
                channel2_id=row[1],
                cosine=row[2])

    def test_calculate_scores(self):
        ratings = [
            Rating(channel=self.channels[0], rating=5),
            Rating(channel=self.channels[4], rating=3)
            ]
        scores, topThree = \
            Similarity.objects.recommend_from_ratings(ratings)
        self.assertEquals(scores, {
                    self.channels[1].id: ((2.5 * 0.5 + 0.5 * -0.1) / 0.6)+2.5,
                    self.channels[2].id: ((2.5 * -0.5 + 0.5 * 0.9) / 1.4)+2.5,
                    self.channels[3].id: ((2.5 * 0.6 + 0.5 * 0.2) / 0.8)+2.5,
                    })
        self.assertEquals(topThree, {
            self.channels[1].id:
                [(0.5 * -0.1, self.channels[4].id),
                    (2.5 * 0.5, self.channels[0].id)],
            self.channels[2].id:
                [(2.5 * -0.5, self.channels[0].id),
                    (0.5 * 0.9, self.channels[4].id)],
            self.channels[3].id:
                [(0.5 * 0.2, self.channels[4].id),
                    (2.5 * 0.6, self.channels[0].id)],
            })
