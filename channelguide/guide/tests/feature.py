import time

from django.conf import settings
from channelguide.testframework import TestCase
from channelguide.guide.models import FeaturedQueue

class FeaturedQueueTestCase(TestCase):

    def setUp(self):
        TestCase.setUp(self)
        self.change_setting_for_test('MAX_FEATURES', 3)
        self.owner = self.make_user('wanda', role='S')
        self.channels = [self.make_channel(self.owner, state='A')
                for i in range(8)]
        self.users = [self.make_user('user%i' % i, role='S')
                for i in range(5)]
        self.old_fq_save = FeaturedQueue.save
        def mockSave(fqself, connection):
            # slow down saves to make distinct timestamps
            self.old_fq_save(fqself, connection)
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
        rows = FeaturedQueue.featured(
                FeaturedQueue.IN_QUEUE).execute(self.connection)
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
            fq = FeaturedQueue.feature_channel(channel, user, self.connection)
            fq.state = FeaturedQueue.PAST
            fq.save(self.connection)
        self.refresh_connection()
        for i in range(3, 6):
            user = self.users[5-i]
            channel = self.channels[i]
            url = channel.get_url()
            self.post_data(url, {'action': 'feature'}, user)
        FeaturedQueue.shuffle_queue(self.connection)
        queue = FeaturedQueue.featured().execute(self.connection)
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
            fq = FeaturedQueue.feature_channel(channel, user, self.connection)
            fq.state = FeaturedQueue.PAST
            fq.save(self.connection)
        self.refresh_connection()
        for i in range(3, 6):
            user = self.users[5-i]
            channel = self.channels[i]
            url = channel.get_url()
            self.post_data(url, {'action': 'feature'}, user)
        FeaturedQueue.feature_channel(self.channels[6], self.users[3],
                self.connection).save(self.connection)
        FeaturedQueue.feature_channel(self.channels[7], self.users[4],
                self.connection).save(self.connection)
        self.refresh_connection()
        FeaturedQueue.shuffle_queue(self.connection)
        queue = FeaturedQueue.featured().execute(self.connection)
        self.check_queue_has_channels(queue, [self.channels[5],
            self.channels[7], self.channels[6]])

    def test_shuffling_removes_oldest_channel(self):
        """
        Shuffling the featured queue when it is full should remove the
        oldest member of the queue by setting it's state to PAST.
        """
        user = self.users[0]
        for c in self.channels[:3]:
            fq = FeaturedQueue.feature_channel(c, user, self.connection)
            fq.state = fq.CURRENT
            fq.save(self.connection)
        FeaturedQueue.feature_channel(self.channels[3], user, self.connection)
        FeaturedQueue.shuffle_queue(self.connection)
        queue = FeaturedQueue.featured().execute(self.connection)
        self.check_queue_has_channels(queue, [self.channels[3],
            self.channels[2], self.channels[1]])

    def test_shuffle_sets_channel_table(self):
        """
        Shuffling the channels should change the featured* columns in the
        channel table.
        """
        user = self.users[0]
        for c in self.channels[:3]:
            FeaturedQueue.feature_channel(c, user, self.connection)
            c = self.refresh_record(c)
            self.assertEquals(c.featured, 0)
        FeaturedQueue.shuffle_queue(self.connection)
        for c in self.channels[:3]:
            fq = FeaturedQueue.get(self.connection, c.id)
            c = self.refresh_record(c)
            self.assertEquals(c.featured, 1)
            self.assertEquals(c.featured_by_id, user.id)
            self.assertEquals(c.featured_at, fq.featured_at)
        for c in self.channels[3:6]:
            # get rid of old features
            FeaturedQueue.feature_channel(c, user, self.connection)
            FeaturedQueue.shuffle_queue(self.connection)
        for c in self.channels[:3]:
            c = self.refresh_record(c)
            self.assertEquals(c.featured, 0)
            fq = FeaturedQueue.get(self.connection, c.id)
            self.assertEquals(fq.state, fq.PAST)

    def test_unfeaturing_channel_in_queue(self):
        """
        Unfeaturing a channel in the queue should remove it from the queue
        entirely.        """
        url = self.channels[0].get_url()
        self.post_data(url, {'action':'feature'}, self.owner)
        self.refresh_connection()
        self.assertEquals(len(FeaturedQueue.query().execute(self.connection)),
                1)
        self.post_data(url, {'action':'unfeature'}, self.owner)
        self.refresh_connection()
        self.assertEquals(list(FeaturedQueue.query().execute(self.connection)),
                [])

    def test_unfeaturing_channel_featured(self):
        """
        Unfeaturing a currently featured channel should move it to
        the past category, and shuffle a new channel into its place.
        """
        url = self.channels[0].get_url()
        for c in self.channels[:4]:
            FeaturedQueue.feature_channel(c, self.owner, self.connection)
        FeaturedQueue.shuffle_queue(self.connection)
        self.refresh_connection()
        self.post_data(url, {'action':'unfeature'}, self.owner)
        self.refresh_connection()
        self.check_queue_has_channels(FeaturedQueue.featured().execute(self.connection),
                [self.channels[3], self.channels[2], self.channels[1]])
        fq = FeaturedQueue.get(self.connection, self.channels[0].id)
        self.assertEquals(fq.state, fq.PAST)

    def test_refeaturing_old_channel(self):
        """
        Refeaturing a previously featured channel should reset its state
        and featured_at time.
        """
        fq = FeaturedQueue.feature_channel(self.channels[0], self.owner,
                self.connection)
        fq.state = fq.PAST
        fq.save(self.connection)
        self.refresh_connection()
        old_featured_time = fq.featured_at
        self.post_data(self.channels[0].get_url(), {'action':'feature'},
                self.owner)
        self.refresh_connection()
        fq = self.refresh_record(fq)
        self.assertEquals(fq.state, fq.IN_QUEUE)
        self.assert_(old_featured_time < fq.featured_at)
        
