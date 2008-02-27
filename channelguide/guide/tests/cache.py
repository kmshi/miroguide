# Copyright (c) 2008 Participatory Culture Foundation
# See LICENSE for details.

from datetime import datetime

from django.conf import settings
from django.http import HttpRequest, HttpResponse

from channelguide import util
from channelguide import cache as cg_cache
# importing it as cache breaks the unit test suite for some reason.
from channelguide.guide.models import Channel
from channelguide.sessions.models import Session
import time, pickle
from channelguide.testframework import TestCase
from sqlhelper.orm import Table, columns

mock_table = Table('test_table',
        columns.Int('id', primary_key=True, auto_increment=True),
        columns.String('name', 200))

class MockCachedRecord(cg_cache.CachedRecord):
    table = mock_table

class CacheTestBase(TestCase):
    def setUp(self):
        TestCase.setUp(self)
        self.change_setting_for_test("DISABLE_CACHE", False)

    def make_request(self, path, query=None):
        request = HttpRequest()
        request.method = "GET"
        request.path = path
        request.META['QUERY_STRING'] = query
        return request

    def make_response(self):
        response = HttpResponse("Hello World")
        responseastatus_code = 200
        return response

    def rand_path(self):
        return '/' + util.random_string(20)

    def is_request_cached(self, path, query=None):
        request = self.make_request(path, query)
        if self.middleware.process_request(request) is None:
            self.middleware.process_response(request, self.make_response())
            return False
        else:
            return True

    def make_request_cached(self, path, query=None):
        request = self.make_request(path, query)
        if self.middleware.process_request(request) is None:
            self.middleware.process_response(request, self.make_response())
        self.assert_(self.is_request_cached(path, query))

class CacheTest(CacheTestBase):
    def setUp(self):
        CacheTestBase.setUp(self)
        self.middleware = cg_cache.middleware.CacheMiddleware()
        time.sleep(1)
        # hack because we may have called memcached.flush_all recently.
        # Because memcached has a resolution of 1 second, we need this to make
        # sure flush_all goes through.
    def test_default_cache_control(self):
        path = self.rand_path()
        request = self.process_request(request=self.make_request(path))
        response = self.process_response(request)
        self.assertEquals(response.headers['Cache-Control'], 'max-age=0')

    def test_manual_cache_control(self):
        path = self.rand_path()
        request = self.process_request(request=self.make_request(path))
        self.middleware.process_request(request)
        response = self.make_response()
        response.headers['Cache-Control'] = 'max-age=123'
        self.process_response_middleware(request, response)
        self.assertEquals(response.headers['Cache-Control'], 'max-age=123')

class CacheMiddlewareTest(CacheTestBase):
    def setUp(self):
        CacheTestBase.setUp(self)
        self.middleware = cg_cache.middleware.CacheMiddleware()
        time.sleep(1) 
        # hack because we may have called memcached.flush_all recently.
        # Because memcached has a resolution of 1 second, we need this to make
        # sure flush_all goes through.

    def tearDown(self):
        cg_cache.clear_cache()
        TestCase.tearDown(self)
    def test_cache(self):
        path = self.rand_path()
        self.assert_(not self.is_request_cached(path))
        self.assert_(self.is_request_cached(path))
        self.assert_(not self.is_request_cached(path, 'foo=bar'))
        self.assert_(self.is_request_cached(path, 'foo=bar'))

    def test_expire(self):
        path = self.rand_path()
        self.make_request_cached(path)
        cg_cache.clear_cache()
        self.assert_(not self.is_request_cached(path))

    def test_expire_on_object_change(self):
        user = self.make_user("kelly")
        channel = self.make_channel(user)
        path = '/channels/popular'
        self.save_to_db(channel)
        time.sleep(1) # see above for why
        self.make_request_cached(path)
        channel.name = "NEW ONE"
        channel.save(self.connection)
        self.assert_(not self.is_request_cached(path))

    def test_session_change_doesnt_expire_cache(self):
        path = self.rand_path()
        self.make_request_cached(path)
        session = Session()
        session.session_key = '123123123'
        session.expires = datetime.now()
        session.set_data({'foo': 'bar'})
        self.save_to_db(session)
        self.assert_(self.is_request_cached(path))

    def test_with_logins(self):
        user = self.make_user("userkelly")
        user2 = self.make_user("userbobby")
        anon_page = self.get_page('/')
        self.login(user)
        kelly_page = self.get_page('/')
        self.login(user2)
        bobby_page = self.get_page('/')
        self.logout()
        anon2_page = self.get_page('/')

        self.assert_('userbobby' not in anon_page.content)
        self.assert_('userbobby' not in kelly_page.content)
        self.assert_('userbobby' in bobby_page.content)
        self.assert_('userbobby' not in anon_page.content)

        self.assert_('userkelly' not in anon_page.content)
        self.assert_('userkelly' in kelly_page.content)
        self.assert_('userkelly' not in bobby_page.content)
        self.assert_('userkelly' not in anon_page.content)

'''
class CachedRecordTest(TestCase):
    def setUp(self):
        TestCase.setUp(self)
        self.connection.execute("""CREATE TABLE test_table (
                id INT(11) NOT NULL AUTO_INCREMENT PRIMARY KEY,
                name VARCHAR(200) DEFAULT NULL) ENGINE=InnoDB""")
        self.change_setting_for_test("DISABLE_CACHE", False)
        cg_cache.client.clear_cache()
        time.sleep(1)
        self.record = MockCachedRecord()
        self.record.id = -1
        self.record.name = "Mock Record"

    def test_save_to_cache(self):
        """
        Test that the save_to_cache() method saves the object into the cache.
        """
        self.record.save_to_cache()
        dictionary = cg_cache.client.get('MockCachedRecord:-1:object')
        self.assertEquals(dictionary['id'], -1)
        self.assertEquals(dictionary['name'], 'Channel Name')
        self.assertEquals(dictionary['description'],
                "Channel Description\nHas a new line")

    def test_load_from_cache(self):
        """
        CachedRecord.load_from_cache should load the object from the cache.
        """
        self.record.save_to_cache()
        time.sleep(1)
        new_record = MockCachedRecord.load_from_cache(-1)
        self.assertEquals(self.record, new_record)

    def test_load_from_cache_list(self):
        """
        CachedRecord.load_from_cache should load the object from the cache when
        the primary key(s) are passed in as a list.
        """
        self.record.save_to_cache()
        new_record = MockCachedRecord.load_from_cache([-1])
        self.assertEquals(self.record, new_record)

    def test_load_from_cache_extra(self):
        """
        CacheRecord.load_from_cache optionally takes a list of extra keys to
        try and load.  These represent joins or loads which are added to the
        object.  They are stored in separate keys, and loaded at the same
        time as the object.
        """
        self.record.save_to_cache()
        cg_cache.client.set(self.record.cache_prefix([-1])+'testload',
                'hello world')
        new_record = MockCachedRecord.load_from_cache(-1, ['testload'])
        self.assertEquals(new_record.testload, 'hello world')

    def test_load_from_cache_extra_failure(self):
        """
        CacheRecord.load_from_cache optionally takes a list of extra keys to
        try and load.  These represent joins or loads which are added to the
        object.  They are stored in separate keys, and loaded at the same
        time as the object.  If the extra keys can't be loaded, then
        the load should fail.
        """
        self.record.save_to_cache()
        new_record = MockCachedRecord.load_from_cache(-1, ['testload'])
        self.assert_(new_record is None)

    def test_insert_adds_to_cache(self):
        """
        CachedRecord.insert() should add the object to the cache.
        """
        del self.record.id # it'll get set
        self.record.insert(self.connection)
        new_record = MockCachedRecord.load_from_cache(self.record.id)
        self.assertEquals(self.record, new_record)

    def test_update_adds_to_cache(self):
        """
        CachedRecord.update() should add the object to the cache.
        """
        del self.record.id # it'll get set
        self.record.insert(self.connection)
        self.record.name = "New Channel Name"
        self.record.update(self.connection)
        new_record = MockCachedRecord.load_from_cache(self.record.id)
        self.assertEquals(self.record, new_record)

    def test_get_goes_to_database(self):
        """
        CachedRecord.get should go to the database if the object is
        not found in the cache.
        """
        new_record = MockCachedRecord.get(self.connection,
                self.channel.primary_key_values())
        self.assertEquals(new_record.id, self.channel.id)
        self.assertEquals(new_record.name, self.channel.name)

    def test_get_inserts_into_cache(self):
        """
        CachedRecord.get should add the object to the cache if it's not found
        there.
        """
        new_record = MockCachedRecord.get(self.connection,
                self.channel.primary_key_values())
        self.assert_(
                cg_cache.client.get(
                    'MockCachedRecord:%i:object' % self.channel.id)
                is not None)

    def test_get_gets_from_cache(self):
        """
        CachedRecord.get should prefer an object out of the cache.
        """
        self.record.save_to_cache()
        new_record = MockCachedRecord.get(None, -1)
        self.assertEquals(self.record, new_record)
        self.assertEquals(new_record.rowid, self.record.rowid)

    def test_get_with_join(self):
        """
        CachedRecord.get with a join should get the object out of the
        cache but perform the join normally.
        """
        self.record.name = "Foobar"
        self.record.save_to_cache()
        new_record = MockCachedRecord.get(self.connection, -1, join=['owner'])
        self.assertEquals(new_record.owner.id, self.user.id)
        self.assertEquals(new_record.name, "Foobar")

'''

if settings.DISABLE_CACHE or not settings.MEMCACHED_SERVERS:
    del CacheTest
    del CacheMiddlewareTest
    del CacheTestBase
