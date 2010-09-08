# Copyright (c) 2008-2009 Participatory Culture Foundation
# See LICENSE for details.

from channelguide.channels.models import Channel
from channelguide.ratings.models import Rating
from channelguide.testframework import TestCase
from django.conf import settings
import re

class RatingsTestBase(TestCase):

    def setUp(self):
        TestCase.setUp(self)
        self.owner = self.make_user('owner')
        self.owner.get_profile().approved = True
        self.owner.get_profile().save()
        self.channel = self.make_channel(self.owner)
        self.users = []
        for rating in range(6):
            user = self.make_user('user%i' % rating)
            user.get_profile().approved = True
            user.get_profile().save()
            self.users.append(user)
            self.rate_channel(self.channel, user, rating)
        self.logout()

    def rate_channel(self, channel, user, rating):
        self.get_page('/feeds/%i/rate' % channel.id, login_as=user,
                data = {'rating': rating})


class RatingTestCase(RatingsTestBase):
    def _find_average_in_page(self, page):
        matches = re.findall('"Average Rating: (\d\.\d*)"', page.content)
        return float(matches[0])

    def _find_user_in_page(self, page):
        matches = re.findall('"User Rating: (\d)"', page.content)
        return int(matches[0])

    def test_unauthenticated_details_has_average(self):
        """
        The unauthenticated details page should show the average rating.
        """
        url = self.channel.get_url()[len(settings.BASE_URL)-1:]
        page = self.get_page(url)
        self.assertEquals(self._find_average_in_page(page), 3)

    def test_unrated_user_details_has_average(self):
        """
        The details page for a user who hasn't rated the channel should show
        the average rating.
        """
        url = self.channel.get_url()[len(settings.BASE_URL)-1:]
        page = self.get_page(url, self.owner)
        self.assertEquals(self._find_average_in_page(page), 3)

    def test_rated_user_details_has_rating(self):
        """
        The details page for a user who has rated the channel should show
        their rating.
        """
        for user in self.users:
            url = self.channel.get_url()[len(settings.BASE_URL)-1:]
            page = self.get_page(url, user)
            rating = Rating.objects.get(user=user, channel=self.channel)
            page_rating = self._find_user_in_page(page)
            if rating.rating is None:
                self.assertEquals(page_rating, 0)
            else:
                self.assertEquals(page_rating, rating.rating)

    def test_rating_needs_login(self):
        """
        An anonymous user who tries to rate a channel should be redirected
        to the login page.
        """
        self.assertLoginRedirect('/feeds/%s/rate' % self.channel.id,
                                 login_as=None)

    def test_new_rating(self):
        """
        Going to the rating page should create a new rating in the database.
        """
        self.rate_channel(self.channel, self.owner, 5)
        self.assertEquals(Rating.objects.get(user=self.owner,
                                             channel=self.channel).rating,
                          5)
        rating = self.channel.rating
        self.assertAlmostEquals(rating.average, 3.333, 3)
        self.assertEquals(rating.count, 6)
        self.assertEquals(rating.total, 20)

    def test_rating_update(self):
        """
        Going to the rating page again should update the old rating.
        """
        self.rate_channel(self.channel, self.users[0], 3)
        self.rate_channel(self.channel, self.users[0], 5)
        self.assertEquals(Rating.objects.get(user=self.users[0],
                                             channel=self.channel).rating,
                          5)
        rating = self.channel.rating
        self.assertAlmostEquals(rating.average, 3.333, 3)
        self.assertEquals(rating.count, 6)
        self.assertEquals(rating.total, 20)

    def test_confirming_a_user_updates_table(self):
        """
        When a user is approved, their ratings should be added to the
        generated ratings table.
        """
        user = self.make_user('foo')
        self.rate_channel(self.channel, user, 5)
        self.assertEquals(self.channel.rating.average, 3)
        self.assertEquals(self.channel.rating.count, 5)
        url = user.get_profile().generate_confirmation_url()
        self.get_page(url[len(settings.BASE_URL_FULL)-1:])
        c = Channel.objects.get(pk=self.channel.pk)
        self.assertAlmostEquals(c.rating.average, 3.333, 3)
        self.assertEquals(c.rating.count, 6)


class GeneratedRatingsTestCase(RatingsTestBase):

    def test_get_average(self):
        """
        Channel.query().join('rating').average should return the average rating
        for the channel.
        """
        self.assertEquals(float(self.channel.rating.average), 3)

    def test_get_average_ignores_unapproved(self):
        """
        Channel.rating.average should ignore ratings from users who are not
        approved.
        """
        new_user = self.make_user('foo')
        self.rate_channel(self.channel, new_user, 5)
        self.assertEquals(float(self.channel.rating.average), 3)
        self.rate_channel(self.channel, new_user, 4)
        self.assertEquals(float(self.channel.rating.average), 3)

    def test_get_average_ignores_null(self):
        """
        Channel.rating.average should ignore NULL ratings.
        """
        new_user = self.make_user('foo')
        new_user.get_profile().approved = 1
        new_user.get_profile().save()
        self.rate_channel(self.channel, new_user, 0)
        self.assertEquals(float(self.channel.rating.average), 3)

    def test_get_count(self):
        """
        Channel.query().join('rating').count should return the number of
        ratings for the channel.
        """
        self.assertEquals(self.channel.rating.count, 5)

    def test_get_count_ignores_unapproved(self):
        """
        Channel.rating.count should ignore ratings from users who are not
        approved.
        """
        new_user = self.make_user('foo')
        self.rate_channel(self.channel, new_user, 5)
        self.assertEquals(self.channel.rating.count, 5)

    def test_get_count_ignores_null(self):
        """
        Channel.rating.count should ignore NULL ratings.
        """
        new_user = self.make_user('foo')
        new_user.get_profile().approved = 1
        new_user.get_profile().save()
        self.rate_channel(self.channel, new_user, 0)
        self.assertEquals(float(self.channel.rating.count), 5)
