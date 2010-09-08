# Copyright (c) 2008-2009 Participatory Culture Foundation
# See LICENSE for details.

import time, datetime

from channelguide.testframework import TestCase
from channelguide.channels.models import Channel
from channelguide.featured.models import FeaturedQueue

class FeaturedQueueTestCase(TestCase):

    def setUp(self):
        TestCase.setUp(self)
        self.change_setting_for_test('MAX_FEATURES', 3)
        self.owner = self.make_user('wanda',
                                    group=['cg_supermoderator'])
        self.channels = [self.make_channel(self.owner, state='A')
                for i in range(8)]
        self.users = [self.make_user('user%i' % i,
                                     group=['cg_supermoderator'])
                for i in range(5)]
        self.old_fq_save = FeaturedQueue.save
        def mockSave(fqself):
            # slow down saves to make distinct timestamps
            self.old_fq_save(fqself)
            time.sleep(1)
        FeaturedQueue.save = mockSave

    def tearDown(self):
        TestCase.tearDown(self)
        FeaturedQueue.save = self.old_fq_save
        del self.old_fq_save

    def check_queue_has_channels(self, queue, channels):
        self.assertEquals([fq.channel_id for fq in queue],
                [c.id for c in channels])

    def test_featuring_channel_adds_to_queue(self):
        """
        Featuring a channel should add it to the queue.
        """
        url = self.channels[0].get_url()
        self.post_data(url, {'action': 'feature'}, self.owner)
        rows = FeaturedQueue.objects.filter(state=
                FeaturedQueue.IN_QUEUE)
        self.check_queue_has_channels(rows, [self.channels[0]])
        self.assertEquals(rows[0].featured_by_id, self.owner.id)

    def test_shuffling_adds_round_robin(self):
        """
        If there are not settings.MAX_FEATURES channels being feature,
        then a new channel from the queue should be added.  The channel(s) to
        be added should be ordered by when their owner last had a channel
        featured (oldest first).
        """
        for i in range(3):
            user = self.users[i]
            channel = self.channels[i]
            fq = FeaturedQueue.objects.feature(channel, user)
            fq.state = FeaturedQueue.PAST
            fq.save()
        for i in range(3, 6):
            user = self.users[5-i]
            channel = self.channels[i]
            url = channel.get_url()
            self.post_data(url, {'action': 'feature'}, user)
        FeaturedQueue.objects.shuffle()
        queue = FeaturedQueue.objects.filter(state=FeaturedQueue.CURRENT)
        self.check_queue_has_channels(queue, [self.channels[3],
            self.channels[4], self.channels[5]])

    def test_shuffling_adds_unfavorited_first(self):
        """
        Any users who have never had a channel featured should go first,
        in the order which their channels were featured.
        """
        for i in range(3):
            user = self.users[i]
            channel = self.channels[i]
            fq = FeaturedQueue.objects.feature(channel, user)
            fq.state = FeaturedQueue.PAST
            fq.save()
        for i in range(3, 6):
            user = self.users[5-i]
            channel = self.channels[i]
            url = channel.get_url()
            self.post_data(url, {'action': 'feature'}, user)
        FeaturedQueue.objects.feature(self.channels[6], self.users[3])
        FeaturedQueue.objects.feature(self.channels[7], self.users[4])
        FeaturedQueue.objects.shuffle()
        queue = FeaturedQueue.objects.filter(state=FeaturedQueue.CURRENT)
        self.check_queue_has_channels(queue, [self.channels[5],
            self.channels[7], self.channels[6]])

    def test_shuffling_removes_oldest_channel(self):
        """
        Shuffling the featured queue when it is full should remove the
        oldest member of the queue by setting it's state to PAST.
        """
        user = self.users[0]
        for c in self.channels[:3]:
            fq = FeaturedQueue.objects.feature(c, user)
            fq.state = fq.CURRENT
            fq.save()
        FeaturedQueue.objects.feature(self.channels[3], user)
        FeaturedQueue.objects.shuffle()
        queue = FeaturedQueue.objects.filter(state=FeaturedQueue.CURRENT)
        self.check_queue_has_channels(queue, [self.channels[3],
            self.channels[2], self.channels[1]])

    def test_shuffle_sets_channel_table(self):
        """
        Shuffling the channels should change the featured* columns in the
        channel table.
        """
        user = self.users[0]
        for c in self.channels[:3]:
            FeaturedQueue.objects.feature(c, user)
            self.assertEquals(Channel.objects.get(pk=c.pk).featured, 0)
        FeaturedQueue.objects.shuffle()
        for c in self.channels[:3]:
            fq = FeaturedQueue.objects.get(channel=c)
            self.assertEquals(fq.channel.featured, 1)
            self.assertEquals(fq.channel.featured_by_id, user.id)
            self.assertEquals(fq.channel.featured_at, fq.featured_at)
        for c in self.channels[3:6]:
            # get rid of old features
            FeaturedQueue.objects.feature(c, user)
            FeaturedQueue.objects.shuffle()
        for c in self.channels[:3]:
            c = Channel.objects.get(pk=c.pk)
            self.assertEquals(c.featured, 0)
            fq = FeaturedQueue.objects.get(channel=c)
            self.assertEquals(fq.state, fq.PAST)

    def test_shuffle_doesnt_error_when_theres_no_queue(self):
        """Shuffling the channels when there's nothing in the queue
        shouldn't raise an error.
        """
        user = self.users[0]
        for c in self.channels[:3]:
            FeaturedQueue.objects.feature(c, user)
            self.assertEquals(Channel.objects.get(pk=c.pk).featured, 0)
        FeaturedQueue.objects.shuffle()
        FeaturedQueue.objects.shuffle()

    def test_unfeaturing_channel_in_queue(self):
        """
        Unfeaturing a channel in the queue should remove it from the queue
        entirely.
        """
        url = self.channels[0].get_url()
        self.post_data(url, {'action':'feature'}, self.owner)
        self.assertEquals(FeaturedQueue.objects.count(),
                1)
        self.post_data(url, {'action':'unfeature'}, self.owner)
        self.assertEquals(FeaturedQueue.objects.count(),
                0)

    def test_unfeaturing_channel_featured(self):
        """
        Unfeaturing a currently featured channel should move it to
        the past category, and shuffle a new channel into its place.
        """
        url = self.channels[0].get_url()
        for c in self.channels[:4]:
            FeaturedQueue.objects.feature(c, self.owner)
        FeaturedQueue.objects.shuffle()
        self.post_data(url, {'action':'unfeature'}, self.owner)
        self.check_queue_has_channels(
            FeaturedQueue.objects.filter(state=FeaturedQueue.CURRENT),
            [self.channels[3], self.channels[2], self.channels[1]])
        fq = FeaturedQueue.objects.get(pk=self.channels[0].id)
        self.assertEquals(fq.state, fq.PAST)

    def test_refeaturing_old_channel(self):
        """
        Refeaturing a previously featured channel should reset its state
        and featured_at time.
        """
        fq = FeaturedQueue.objects.feature(self.channels[0], self.owner)
        fq.state = fq.PAST
        fq.save()
        old_featured_time = fq.featured_at
        self.post_data(self.channels[0].get_url(), {'action':'feature'},
                self.owner)
        fq = FeaturedQueue.objects.get(pk=fq.pk)
        self.assertEquals(fq.state, fq.IN_QUEUE)
        self.assert_(old_featured_time < fq.featured_at)

    def test_last_time(self):
        """
        The last time subquery should return the most-recent time the featuring
        user has had a channel featured on the front page (states 1 or 2).
        """
        times = {}
        for i in range(3):
            fq = FeaturedQueue.objects.feature(self.channels[i],
                                               self.users[i])
            fq.state = fq.PAST
            times[self.users[i].id] = fq.featured_at.replace(microsecond=0)
            fq.save()
        fq = FeaturedQueue.objects.feature(self.channels[3],
                                           self.users[0])
        fq.state = fq.CURRENT
        fq.save()
        times[self.users[0].id] = fq.featured_at.replace(microsecond=0)
        for i in range(4):
            fq = FeaturedQueue.objects.feature(self.channels[i+4],
                                               self.users[i])
        fqs = FeaturedQueue.objects._with_last_time().filter(
            state=FeaturedQueue.IN_QUEUE)
        for fq in fqs:
            if fq.last_time == '0':
                self.assertFalse(fq.featured_by_id in times)
            else:
                dt = datetime.datetime.strptime(fq.last_time,
                                                '%Y-%m-%d %H:%M:%S')
                self.assertEquals(dt, times[fq.featured_by_id])
