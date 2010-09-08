# Copyright (c) 2009 Participatory Culture Foundation
# See LICENSE for details.

from django.conf import settings
from django.db.models import Count
from channelguide.testframework import TestCase

from channelguide.channels.models import Channel
from channelguide.flags.models import Flag

class FlaggingModelTestCase(TestCase):

    def setUp(self):
        TestCase.setUp(self)
        self.owner = self.make_user('owner')
        self.channel = self.make_channel(self.owner)

    def _get_flags(self):
        return Flag.objects.all()

    def test_add_flag(self):
        """
        Channel.add_flag() should add flag to the channel.
        """
        Flag.objects.get_or_create(channel=self.channel, user=self.owner,
                            flag=Flag.NOT_HD)
        flags = self._get_flags()
        self.assertEquals(len(flags), 1)
        self.assertEquals(flags[0].channel, self.channel)
        self.assertEquals(flags[0].user, self.owner)
        self.assertEquals(flags[0].flag, Flag.NOT_HD)

    def test_add_flag_without_user(self):
        """
        """
        Flag.objects.get_or_create(channel=self.channel, user=None,
                                   flag=Flag.NOT_HD)
        flags = self._get_flags()
        self.assertEquals(len(flags), 1)
        self.assertEquals(flags[0].channel_id, self.channel.id)
        self.assertEquals(flags[0].user_id, None)
        self.assertEquals(flags[0].flag, Flag.NOT_HD)

    def test_no_duplicate_flags(self):
        """
        Calling add_flag() twice shouldn't add duplicate items to the DB.
        """
        Flag.objects.get_or_create(channel=self.channel, user=self.owner,
                                   flag=Flag.NOT_HD)
        Flag.objects.get_or_create(channel=self.channel, user=self.owner,
                                   flag=Flag.NOT_HD)

        flags = self._get_flags()
        self.assertEquals(len(flags), 1)

    def test_no_duplicate_flags_from_anonymous(self):
        """
        All anonymous users count as a single person for counting duplicate
        flags.
        """
        Flag.objects.get_or_create(channel=self.channel, user=None,
                                   flag=Flag.NOT_HD)
        Flag.objects.get_or_create(channel=self.channel, user=None,
                                   flag=Flag.NOT_HD)
        flags = self._get_flags()
        self.assertEquals(len(flags), 1)

    def test_flags_to_multiple_channels(self):
        """
        A single user should be able to flag multiple channels.
        """
        new_channel = self.make_channel(self.owner)
        Flag.objects.get_or_create(channel=self.channel, user=self.owner,
                                   flag=Flag.NOT_HD)
        Flag.objects.get_or_create(channel=new_channel, user=self.owner,
                                   flag=Flag.NOT_HD)
        flags = self._get_flags()
        self.assertEquals(len(flags), 2)

    def test_flags_from_multiple_users(self):
        """
        A single channel should accept flags from multiple users.
        """
        new_user = self.make_user('new')
        Flag.objects.get_or_create(channel=self.channel, user=self.owner,
                                   flag=Flag.NOT_HD)
        Flag.objects.get_or_create(channel=self.channel, user=new_user,
                                   flag=Flag.NOT_HD)
        flags = self._get_flags()
        self.assertEquals(len(flags), 2)

    def test_channel_flag_count(self):
        """
        Test that the subquery 'flag_count' returns the number of flags that
        the channel has.
        """
        Flag.objects.get_or_create(channel=self.channel, user=self.owner,
                                   flag=Flag.NOT_HD)
        Flag.objects.get_or_create(channel=self.channel, user=None,
                                   flag=Flag.NOT_HD)
        self.assertEquals(self.channel.flags.count(), 2)

    def test_order_by_flag_count(self):
        """
        Test that ordering based on the flag count works correctly.
        """
        Flag.objects.get_or_create(channel=self.channel, user=self.owner,
                                   flag=Flag.NOT_HD)
        Flag.objects.get_or_create(channel=self.channel, user=None,
                                   flag=Flag.NOT_HD)
        new_channel = self.make_channel(self.owner)
        Flag.objects.get_or_create(channel=new_channel, user=self.owner,
                                   flag=Flag.NOT_HD)

        channels = Channel.objects.annotate(Count('flags')).order_by(
            'flags__count')
        self.assertEquals(len(channels), 2)
        self.assertEquals(channels[0].id, new_channel.id)
        self.assertEquals(channels[1].id, self.channel.id)

        channels = Channel.objects.annotate(Count('flags')).order_by(
            '-flags__count')
        self.assertEquals(len(channels), 2)
        self.assertEquals(channels[0].id, self.channel.id)
        self.assertEquals(channels[1].id, new_channel.id)


    def test_flag_count(self):
        """
        Flag.count() should return the number of channels which have the
        specified kind of flag.
        """
        Flag.objects.get_or_create(channel=self.channel, user=self.owner,
                                   flag=Flag.NOT_HD)
        Flag.objects.get_or_create(channel=self.channel, user=self.owner,
                                   flag=999)
        Flag.objects.get_or_create(channel=self.channel,
                                   flag=999)

        new_channel = self.make_channel(self.owner)
        Flag.objects.get_or_create(channel=new_channel, user=self.owner,
                                   flag=Flag.NOT_HD)
        Flag.objects.get_or_create(channel=new_channel,
                                   flag=Flag.NOT_HD)

        self.assertEquals(Flag.objects.filter(flag=Flag.NOT_HD).count(), 2)
        self.assertEquals(Flag.objects.filter(flag=999).count(), 1)

class FlaggingViewTestCase(TestCase):

    def setUp(self):
        TestCase.setUp(self)
        self.owner = self.make_user('owner')
        self.channel = self.make_channel(self.owner)

    def _flag_url(self):
        url = self.channel.get_flag_url()
        return url[len(settings.BASE_URL_FULL)-1:]

    def _channel_flags(self):
        return Flag.objects.filter(channel=self.channel)

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
