from channelguide.guide.models import Channel, Rating
from channelguide.guide.views import channels
from channelguide.guide import tables
from channelguide.testframework import TestCase
from channelguide import manage, settings
import re

class ChannelRatingsTest(TestCase):

    def setUp(self):
        TestCase.setUp(self)
        self.owner = self.make_user('owner')
        self.channel = self.make_channel(self.owner)
        self.users = []
        for rating in range(6):
            user = self.make_user('user%i' % rating)
            user.approved = 1
            user.save(self.connection)
            self.users.append(user)
            r = Rating()
            r.user_id = user.id
            r.channel_id = self.channel.id
            r.rating = rating
            r.save(self.connection)
        self.connection.commit()

    def test_get_average(self):
        """
        Channel.average_rating should return the average rating for the
        channel.
        """
        self.assertEquals(float(self.channel.average_rating(self.connection)),
                2.5)

    def test_get_average_ignores_unapproved(self):
        """
        Channel.average_rating should ignore ratings from users who are not
        approved.
        """
        new_user = self.make_user('foo')
        r = Rating()
        r.rating = 5
        r.channel_id = self.channel.id
        r.user_id = new_user.id
        r.save(self.connection)
        self.assertEquals(float(self.channel.average_rating(self.connection)),
                2.5)

    def test_get_count(self):
        """
        Channel.count_rating should return the number of ratings for the
        channel.
        """
        self.assertEquals(self.channel.count_rating(self.connection),
                6)

    def test_get_count_ignores_unapproved(self):
        """
        Channel.count_rating should ignore ratings from users who are not
        approved.
        """
        new_user = self.make_user('foo')
        r = Rating()
        r.rating = 5
        r.channel_id = self.channel.id
        r.user_id = new_user.id
        r.save(self.connection)
        self.assertEquals(float(self.channel.count_rating(self.connection)),
                6)


    def test_unauthenticated_details_has_average(self):
        """
        The unauthenticated details page should show the average rating.
        """
        url = self.channel.get_url()[len(settings.BASE_URL)-1:]
        page = self.get_page(url)
        matches = re.findall('Average Rating: (\d\.\d*)', page.content)
        self.assertEquals(float(matches[0]), 2.5)

    def test_unrated_user_details_has_average(self):
        """
        The details page for a user who hasn't rated the channel should show
        the average rating.
        """
        url = self.channel.get_url()[len(settings.BASE_URL)-1:]
        page = self.get_page(url, self.owner)
        matches = re.findall('Average Rating: (\d\.\d*)', page.content)
        self.assertEquals(float(matches[0]), 2.5)

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
            self.assertEquals(float(matches[0]), rating.rating)

    def test_rating_needs_login(self):
        """
        An anonymous user who tries to rate a channel should be redirected
        to the login page.
        """
        url = '/channels/rate/%i' % self.channel.id
        self.assertLoginRedirect(url)

    def test_new_rating(self):
        """
        Going to the rating page should create a new rating in the database.
        """
        page = self.get_page('/channels/rate/%i' % self.channel.id,
                self.owner, {'rating': '3'})
        self.assertEquals(float(Rating.query(Rating.c.user_id==self.owner.id,
            Rating.c.channel_id==self.channel.id).get(self.connection).rating),
            3)

    def test_rating_update(self):
        """
        Going to the rating page again should update the old rating.
        """
        page = self.get_page('/channels/rate/%i' % self.channel.id,
                self.users[0], {'rating': '3'})
        self.assertEquals(float(Rating.query(Rating.c.user_id==self.users[0].id,
            Rating.c.channel_id==self.channel.id).get(self.connection).rating),
            3)

