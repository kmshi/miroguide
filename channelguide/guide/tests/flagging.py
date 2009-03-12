# Copyright (c) 2009 Participatory Culture Foundation
# See LICENSE for details.

from django.conf import settings
from channelguide.testframework import TestCase

from channelguide.guide.models import Channel, Flag

class FlaggingModelTestCase(TestCase):

    def setUp(self):
        TestCase.setUp(self)
        self.owner = self.make_user('owner')
        self.channel = self.make_channel(self.owner)

    def _get_flags(self):
        return Flag.query().execute(self.connection)

    def test_add_flag(self):
        """
        Channel.add_flag() should add flag to the channel.
        """
        self.channel.add_flag(self.connection, self.owner, Flag.NOT_HD)
        flags = self._get_flags()
        self.assertEquals(len(flags), 1)
        self.assertEquals(flags[0].channel_id, self.channel.id)
        self.assertEquals(flags[0].user_id, self.owner.id)
        self.assertEquals(flags[0].flag, Flag.NOT_HD)

    def test_add_flag_without_user(self):
        """
        """
        self.channel.add_flag(self.connection, None, Flag.NOT_HD)
        flags = self._get_flags()
        self.assertEquals(len(flags), 1)
        self.assertEquals(flags[0].channel_id, self.channel.id)
        self.assertEquals(flags[0].user_id, None)
        self.assertEquals(flags[0].flag, Flag.NOT_HD)

    def test_no_duplicate_flags(self):
        """
        Calling add_flag() twice shouldn't add duplicate items to the DB.
        """
        self.channel.add_flag(self.connection, self.owner, Flag.NOT_HD)
        self.channel.add_flag(self.connection, self.owner, Flag.NOT_HD)
        flags = self._get_flags()
        self.assertEquals(len(flags), 1)

    def test_no_duplicate_flags_from_anonymous(self):
        """
        All anonymous users count as a single person for counting duplicate flags.
        """
        self.channel.add_flag(self.connection, None, Flag.NOT_HD)
        self.channel.add_flag(self.connection, None, Flag.NOT_HD)
        flags = self._get_flags()
        self.assertEquals(len(flags), 1)

    def test_flags_to_multiple_channels(self):
        """
        A single user should be able to flag multiple channels.
        """
        new_channel = self.make_channel(self.owner)
        self.channel.add_flag(self.connection, self.owner, Flag.NOT_HD)
        new_channel.add_flag(self.connection, self.owner, Flag.NOT_HD)
        flags = self._get_flags()
        self.assertEquals(len(flags), 2)

    def test_flags_from_multiple_users(self):
        """
        A single channel should accept flags from multiple users.
        """
        new_user = self.make_user('new')
        self.channel.add_flag(self.connection, self.owner, Flag.NOT_HD)
        self.channel.add_flag(self.connection, new_user, Flag.NOT_HD)
        flags = self._get_flags()
        self.assertEquals(len(flags), 2)

    def test_channel_flag_count(self):
        """
        Test that the subquery 'flag_count' returns the number of flags that
        the channel has.
        """
        self.channel.add_flag(self.connection, self.owner, Flag.NOT_HD)
        self.channel.add_flag(self.connection, None, Flag.NOT_HD)
        query = Channel.query(Channel.c.id == self.channel.id).load('flag_count')
        new_channel = query.get(self.connection)
        self.assertEquals(new_channel.flag_count, 2)

    def test_order_by_flag_count(self):
        """
        Test that ordering based on the flag count works correctly.
        """
        self.channel.add_flag(self.connection, self.owner, Flag.NOT_HD)
        self.channel.add_flag(self.connection, None, Flag.NOT_HD)
        new_channel = self.make_channel(self.owner)
        new_channel.add_flag(self.connection, self.owner, Flag.NOT_HD)

        query = Channel.query().load('flag_count')
        query.order_by('flag_count')
        channels = query.execute(self.connection)
        self.assertEquals(len(channels), 2)
        self.assertEquals(channels[0].id, new_channel.id)
        self.assertEquals(channels[1].id, self.channel.id)

        query = Channel.query().load('flag_count')
        query.order_by('flag_count', desc=True)
        channels = query.execute(self.connection)
        self.assertEquals(len(channels), 2)
        self.assertEquals(channels[0].id, self.channel.id)
        self.assertEquals(channels[1].id, new_channel.id)


    def test_flag_count(self):
        """
        Flag.count() should return the number of channels which have the specified kind of flag.
        """
        self.channel.add_flag(self.connection, self.owner, Flag.NOT_HD)
        self.channel.add_flag(self.connection, None, 999)
        self.channel.add_flag(self.connection, self.owner, 999)
        new_channel = self.make_channel(self.owner)
        new_channel.add_flag(self.connection, self.owner, Flag.NOT_HD)
        new_channel.add_flag(self.connection, None, Flag.NOT_HD)

        self.assertEquals(Flag.count(self.connection, Flag.NOT_HD), 2)
        self.assertEquals(Flag.count(self.connection, 999), 1)

class FlaggingViewTestCase(TestCase):

    def setUp(self):
        TestCase.setUp(self)
        self.owner = self.make_user('owner')
        self.channel = self.make_channel(self.owner)

    def _flag_url(self):
        url = self.channel.get_flag_url()
        return url[len(settings.BASE_URL_FULL)-1:]

    def _channel_flags(self):
        new_channel = self.refresh_record(self.channel, 'flags')
        return new_channel.flags

    def test_flag_view(self):
        """
        Hitting get_flag_url() with a ;'flag' query string should add a flag to
        the DB for the logged-in user.
        """
        url = self._flag_url()
        response = self.get_page(url, self.owner, {'flag': Flag.NOT_HD})
        self.assertRedirect(response, self.channel.get_url())
        flags = self._channel_flags()
        self.assertEquals(len(flags), 1)
        self.assertEquals(flags[0].user_id, self.owner.id)
        self.assertEquals(flags[0].flag, Flag.NOT_HD)

    def test_flagging_accepts_post(self):
        """
        POSTing the flag argument should also work.
        """
        url = self._flag_url()
        response = self.post_data(url, {'flag': Flag.NOT_HD}, self.owner)
        self.assertRedirect(response, self.channel.get_url())
        flags = self._channel_flags()
        self.assertEquals(len(flags), 1)
        self.assertEquals(flags[0].user_id, self.owner.id)
        self.assertEquals(flags[0].flag, Flag.NOT_HD)

    def test_flagging_does_not_require_login(self):
        """
        Flagging a channel shouldn't require being logged in.
        """
        url = self._flag_url()
        response = self.get_page(url, data={'flag': Flag.NOT_HD})
        self.assertRedirect(response, self.channel.get_url())
        flags = self._channel_flags()
        self.assertEquals(len(flags), 1)
        self.assertEquals(flags[0].user_id, None)
        self.assertEquals(flags[0].flag, Flag.NOT_HD)

    def test_flagging_requires_flag(self):
        """
        Forgetting to pass a flag argument or passing an invalid argument
        should result in a 404.
        """
        url = self._flag_url()
        response = self.get_page(url, self.owner)
        self.assertEquals(response.status_code, 404)

        response = self.get_page(url, self.owner, {'flag': 'invalid'})
        self.assertEquals(response.status_code, 404)

    def test_flagging_requires_channel(self):
        """
        Flagging on an invalid channel should result in a 404.
        """
        url = self._flag_url()
        url = url.replace(str(self.channel.id), '9999')
        response = self.get_page(url, self.owner)
        self.assertEquals(response.status_code, 404)
