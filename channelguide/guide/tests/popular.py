from channelguide.testframework import TestCase
from channelguide.cache import client
from channelguide.guide import popular
from channelguide.guide.models import Channel
import time, datetime

class PopularTestCase(TestCase):

    def setUp(self):
        TestCase.setUp(self)
        user = self.make_user('test')
        ip0 = '0.0.0.0'
        ip1 = '1.1.1.1'
        ip2 = '2.2.2.2'
        yesterday = datetime.datetime.now() - datetime.timedelta(days=1)
        monthago = datetime.datetime.now() - datetime.timedelta(days=33)
        self.old_throttle = Channel._should_throttle_ip_address
        Channel._should_throttle_ip_address= lambda *a: False
        self.channel1 = self.make_channel(user, state='A')
        self.channel1.add_subscription(self.connection, ip0)
        self.channel2 = self.make_channel(user, state='A')
        self.channel2.add_subscription(self.connection, ip0)
        self.channel2.add_subscription(self.connection, ip1, timestamp=yesterday)
        self.channel3 = self.make_channel(user, state='A')
        self.channel3.add_subscription(self.connection, ip0)
        self.channel3.add_subscription(self.connection, ip1, timestamp=yesterday)
        self.channel3.add_subscription(self.connection, ip2, timestamp=monthago)
        self.channel4 = self.make_channel(user)
        self.channel4.add_subscription(self.connection, ip0)
        self.channel4.add_subscription(self.connection, ip1)
        self.channel4.add_subscription(self.connection, ip2)
        client.clear_cache()
        time.sleep(1)

    def tearDown(self):
        TestCase.tearDown(self)
        Channel._should_throttle_ip_address = self.old_throttle
        del self.old_throttle

    def _popular_ids(self, name, limit=None):
        if name is None:
            attr = 'subscription_count'
        else:
            attr = 'subscription_count_' + name
        return [(c.id, getattr(c, attr))
                for c in popular.get_popular(name, self.connection,
                    limit=limit)]

    def test_popular_returns_correct_results(self):
        """
        get_popular should, given a name, return a list of channels sorted
        by the popularity with the 'subscription_count_*' attribute set to
        the count.
        """
        self.assertEquals(self._popular_ids(None), [(self.channel3.id, 3),
            (self.channel2.id, 2), (self.channel1.id, 1)])
        self.assertEquals(self._popular_ids('month'), [(self.channel3.id, 2),
            (self.channel2.id, 2), (self.channel1.id, 1)])
        self.assertEquals(self._popular_ids('today'), [(self.channel3.id, 1),
            (self.channel2.id, 1), (self.channel1.id, 1)])

    def test_limit(self):
        """
        The limit kwarg should::
            * restrict the the top n results if it's a number
            * return a slice from the list starting at limit[0] and containing
                limit[1] items if it's a sequence
        """
        self.assertEquals(self._popular_ids(None, limit=2),
                [(self.channel3.id, 3), (self.channel2.id, 2)])
        self.assertEquals(self._popular_ids(None, limit=(1, 2)),
            [(self.channel2.id, 2), (self.channel1.id, 1)])

    def test_today_sets_cache(self):
        """
        Getting today's count should set the
        'Count:<id>:<year>:<month>:<day>' key to the count for that
        channel.
        """
        popular.get_popular('today', self.connection)
        today = datetime.date.today()
        self.assertEquals(client.get(popular._cache_key(self.channel3.id,
            'today')), 1)

    def test_month_sets_cache(self):
        """
        Getting this month's count should set the
        'Count:<id>:<year>:<month>' key to the count for that
        channel.
        """
        popular.get_popular('month', self.connection)
        today = datetime.date.today()
        self.assertEquals(client.get(popular._cache_key(self.channel3.id,
            'month')), 2)

    def test_all_sets_cache(self):
        """
        Getting the total count should set the
        'Count:<id>' key to the count for that
        channel.
        """
        popular.get_popular(None, self.connection)
        today = datetime.date.today()
        self.assertEquals(client.get('Count:%i' % self.channel3.id), 3)

    def test_today_gets_from_cache(self):
        """
        Getting today's count should try to get the
        'Count:<id>:<year>:<month>:<day> key for the value,
        """
        today = datetime.date.today()
        client.set(popular._cache_key(self.channel1.id, 'today'), 500)
        channels = popular.get_popular('today', self.connection)
        self.assertEquals(channels[0].id, self.channel1.id)
        self.assertEquals(channels[0].subscription_count_today, 500)
        self.assertEquals(channels[1].subscription_count_today, 1)

    def test_month_gets_from_cache(self):
        """
        Getting this month's count should try to get the
        'Count:<id>:<year>:<month> key for the value,
        """
        today = datetime.date.today()
        client.set(popular._cache_key(self.channel1.id, 'month'), 500)
        channels = popular.get_popular('month', self.connection)
        self.assertEquals(channels[0].id, self.channel1.id)
        self.assertEquals(channels[0].subscription_count_month, 500)
        self.assertEquals(channels[1].subscription_count_month, 2)

    def test_total_gets_from_cache(self):
        """
        Getting the total count should try to get the
        'Count:<id> key for the value,
        """
        client.set('Count:%i' % self.channel1.id, 500)
        channels = popular.get_popular(None, self.connection)
        self.assertEquals(channels[0].id, self.channel1.id)
        self.assertEquals(channels[0].subscription_count, 500)
        self.assertEquals(channels[1].id, self.channel3.id)
        self.assertEquals(channels[1].subscription_count, 3)

    def test_use_cache(self):
        """
        If the use_cache kwarg is False, don't get values out of the cache.
        """
        today = datetime.date.today()
        client.set(popular._cache_key(self.channel1.id, 'today'), 500)
        client.set(popular._cache_key(self.channel1.id, 'month'), 500)
        client.set('Count:%i' % self.channel1.id, 500)
        channels = popular.get_popular('today', self.connection,
                use_cache=False)
        self.assertEquals(channels[0].subscription_count_today, 1)
        channels = popular.get_popular('month', self.connection,
                use_cache=False)
        self.assertEquals(channels[0].subscription_count_month, 2)
        channels = popular.get_popular(None, self.connection,
                use_cache=False)
        self.assertEquals(channels[0].subscription_count, 3)


    def test_alternate_query(self):
        """
        An alternate query should be able to be used in place of
        Channel.query_approved().
        """
        query = Channel.query(Channel.c.state=='N')
        channels = popular.get_popular(None, self.connection, query=query)
        self.assertEquals(len(channels), 1)
        self.assertEquals(channels[0].id, self.channel4.id)
        self.assertEquals(channels[0].subscription_count, 3)

    def test_add_subscription_today(self):
        """
        Addding a subscription should show the higher subscription count
        in the cache.
        """
        self.channel3.add_subscription(self.connection, '3.3.3.3')
        id = self.channel3.id
        self.assertEquals(client.get(popular._cache_key(id, None)), 4)
        self.assertEquals(client.get(popular._cache_key(id, 'month')), 3)
        self.assertEquals(client.get(popular._cache_key(id, 'today')), 2)


    def test_add_subscription_month(self):
        """
        Addding a subscription should show the higher subscription count in
        the cache.
        If the timestamp is not within today, it should not increase
        today's count.
        """
        popular.get_popular('today', self.connection) # set the today values
        delta = datetime.timedelta(days=1, minutes=5)
        self.channel3.add_subscription(self.connection, '3.3.3.3',
                timestamp=datetime.datetime.now()-delta)
        id = self.channel3.id
        self.assertEquals(client.get(popular._cache_key(id, None)), 4)
        self.assertEquals(client.get(popular._cache_key(id, 'month')), 3)
        self.assertEquals(client.get(popular._cache_key(id, 'today')), 1)

    def test_add_subscription_total(self):
        """
        Addding a subscription should show the higher subscription count in
        the cache.
        If the timestamp is not within this month, it should not increase
        the month or today counts.
        """
        popular.get_popular('today', self.connection) # set the today values
        popular.get_popular('month', self.connection) # set the month values
        delta = datetime.timedelta(days=32)
        self.channel3.add_subscription(self.connection, '3.3.3.3',
                timestamp=datetime.datetime.now()-delta)
        id = self.channel3.id
        self.assertEquals(client.get(popular._cache_key(id, None)), 4)
        self.assertEquals(client.get(popular._cache_key(id, 'month')), 2)
        self.assertEquals(client.get(popular._cache_key(id, 'today')), 1)

    def test_incr_subscription_today(self):
        """
        Addding a subscription should increase the value in the cache.  If
        possible, it should do this by using the 'incr' command instead of
        doing a database query.
        """
        id = self.channel3.id
        for name in None, 'month', 'today':
            client.set(popular._cache_key(id, name), 500)
        self.channel3.add_subscription(self.connection, '3.3.3.3')
        self.assertEquals(client.get(popular._cache_key(id, None)), 501)
        self.assertEquals(client.get(popular._cache_key(id, 'month')), 501)
        self.assertEquals(client.get(popular._cache_key(id, 'today')), 501)

    def test_incr_subscription_month(self):
        """
        Addding a subscription should increase the value in the cache.  If
        possible, it should do this by using the 'incr' command instead of
        doing a database query.
        If the timestamp is not within today, it should not increment the
        today count.
        """
        id = self.channel3.id
        for name in None, 'month', 'today':
            client.set(popular._cache_key(id, name), 500)
        delta = datetime.timedelta(days=1, minutes=5)
        self.channel3.add_subscription(self.connection, '3.3.3.3',
                timestamp=datetime.datetime.now()-delta)
        self.assertEquals(client.get(popular._cache_key(id, None)), 501)
        self.assertEquals(client.get(popular._cache_key(id, 'month')), 501)
        self.assertEquals(client.get(popular._cache_key(id, 'today')), 500)

    def test_incr_subscription_total(self):
        """
        Addding a subscription should increase the value in the cache.  If
        possible, it should do this by using the 'incr' command instead of
        doing a database query.
        If the timestamp is not within the month, it should only increment
        the total subscription count.
        """
        id = self.channel3.id
        for name in None, 'month', 'today':
            client.set(popular._cache_key(id, name), 500)
        delta = datetime.timedelta(days=32)
        self.channel3.add_subscription(self.connection, '3.3.3.3',
                timestamp=datetime.datetime.now()-delta)
        self.assertEquals(client.get(popular._cache_key(id, None)), 501)
        self.assertEquals(client.get(popular._cache_key(id, 'month')), 500)
        self.assertEquals(client.get(popular._cache_key(id, 'today')), 500)

