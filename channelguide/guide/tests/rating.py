# Copyright (c) 2008 Participatory Culture Foundation
# See LICENSE for details.

from channelguide.guide.models import Channel, Rating
from channelguide.guide.views import channels
from channelguide.guide import tables
from channelguide.testframework import TestCase
from channelguide import manage
from django.conf import settings
import re

class ChannelRatingsTest(TestCase):

    def setUp(self):
        TestCase.setUp(self)
        self.owner = self.make_user('owner')
        self.owner.approved = 1
        self.owner.save(self.connection)
        self.channel = self.make_channel(self.owner)
        self.users = []
        for rating in range(6):
            user = self.make_user('user%i' % rating)
            user.approved = 1
            user.save(self.connection)
            self.users.append(user)
            self.rate_channel(self.channel, user, rating)
            self.connection.commit()
        self.logout()

    def rate_channel(self, channel, user, rating):
        self.refresh_connection()
        self.get_page('/channels/rate/%i' % channel.id, login_as=user,
                data = {'rating': rating})
        self.refresh_connection()

    def test_get_average(self):
        """
        Channel.query().join('rating').average should return the average rating
        for the channel.
        """
        c = self.channel.query().join('rating').get(self.connection)
        self.assertEquals(float(c.rating.average), 3)

    def test_get_average_ignores_unapproved(self):
        """
        Channel.rating.average should ignore ratings from users who are not
        approved.
        """
        new_user = self.make_user('foo')
        self.rate_channel(self.channel, new_user, 5)
        c = self.channel.query().join('rating').get(self.connection)
        self.assertEquals(float(c.rating.average), 3)
        self.rate_channel(self.channel, new_user, 4)
        c = self.channel.query().join('rating').get(self.connection)
        self.assertEquals(float(c.rating.average), 3)

    def test_get_average_ignores_null(self):
        """
        Channel.rating.average should ignore NULL ratings.
        """
        new_user = self.make_user('foo')
        new_user.approved = 1
        new_user.save(self.connection)
        self.rate_channel(self.channel, new_user, 0)
        c = self.channel.query().join('rating').get(self.connection)
        self.assertEquals(float(c.rating.average), 3)

    def test_get_count(self):
        """
        Channel.query().join('rating').count should return the number of
        ratings for the channel.
        """
        c = self.channel.query().join('rating').get(self.connection)
        self.assertEquals(c.rating.count, 5)

    def test_get_count_ignores_unapproved(self):
        """
        Channel.rating.count should ignore ratings from users who are not
        approved.
        """
        new_user = self.make_user('foo')
        self.rate_channel(self.channel, new_user, 5)
        c = self.channel.query().join('rating').get(self.connection)
        self.assertEquals(c.rating.count, 5)

    def test_get_count_ignores_null(self):
        """
        Channel.rating.count should ignore NULL ratings.
        """
        new_user = self.make_user('foo')
        new_user.approved = 1
        new_user.save(self.connection)
        self.rate_channel(self.channel, new_user, 0)
        c = self.channel.query().join('rating').get(self.connection)
        self.assertEquals(float(c.rating.count), 5)


    def test_unauthenticated_details_has_average(self):
        """
        The unauthenticated details page should show the average rating.
        """
        url = self.channel.get_url()[len(settings.BASE_URL)-1:]
        page = self.get_page(url)
        matches = re.findall('Average Rating: (\d\.\d*)', page.content)
        self.assertEquals(float(matches[0]), 3)

    def test_unrated_user_details_has_average(self):
        """
        The details page for a user who hasn't rated the channel should show
        the average rating.
        """
        url = self.channel.get_url()[len(settings.BASE_URL)-1:]
        page = self.get_page(url, self.owner)
        matches = re.findall('Average Rating: (\d\.\d*)', page.content)
        self.assertEquals(float(matches[0]), 3)

    def test_rated_user_details_has_rating(self):
        """
        The details page for a user who has rated the channel should show
        their rating.
        """
        for user in self.users:
            url = self.channel.get_url()[len(settings.BASE_URL)-1:]
            page = self.get_page(url, user)
            rating = Rating.query(Rating.c.user_id==user.id,
                    Rating.c.channel_id==self.channel.id).get(self.connection)
            matches = re.findall('User Rating: (\d[\.\d*]*)', page.content)
            if rating.rating is None:
                self.assertEquals(matches[0], "0")
            else:
                self.assertEquals(float(matches[0]), rating.rating)

    def test_rating_needs_login(self):
        """
        An anonymous user who tries to rate a channel should be redirected
        to the login page.
        """
        url = '/channels/rate/%i' % self.channel.id
        self.assertLoginRedirect(url, login_as=None)

    def test_new_rating(self):
        """
        Going to the rating page should create a new rating in the database.
        """
        page = self.get_page('/channels/rate/%i' % self.channel.id,
                self.owner, {'rating': '5'})
        self.assertEquals(float(Rating.query(Rating.c.user_id==self.owner.id,
            Rating.c.channel_id==self.channel.id).get(self.connection).rating),
            5)
        rating = self.channel.query().join('rating').get(self.connection,
                self.channel.id).rating
        self.assertEquals(rating.average, 3.3)
        self.assertEquals(rating.count, 6)
        self.assertEquals(rating.total, 20)

    def test_rating_update(self):
        """
        Going to the rating page again should update the old rating.
        """
        self.rate_channel(self.channel, self.users[0], 3)
        page = self.get_page('/channels/rate/%i' % self.channel.id,
                self.users[0], {'rating': '5'})
        self.assertEquals(float(Rating.query(Rating.c.user_id==self.users[0].id,
            Rating.c.channel_id==self.channel.id).get(self.connection).rating),
            5)
        rating = self.channel.query().join('rating').get(self.connection,
                self.channel.id).rating
        self.assertEquals(rating.average, 3.3)
        self.assertEquals(rating.count, 6)
        self.assertEquals(rating.total, 20)

    def test_confirming_a_user_updates_table(self):
        """
        When a user is approved, their ratings should be added to the
        generated ratings table.
        """
        user = self.make_user('foo')
        self.rate_channel(self.channel, user, 5)
        c = self.channel.query().join('rating').get(self.connection)
        self.assertEquals(c.rating.average, 3)
        self.assertEquals(c.rating.count, 5)
        url = user.generate_confirmation_url()[len(settings.BASE_URL_FULL)-1:]
        response = self.get_page(url)
        self.refresh_connection()
        c = self.channel.query().join('rating').get(self.connection)
        self.assertEquals(c.rating.average, 3.3)
        self.assertEquals(c.rating.count, 6)

