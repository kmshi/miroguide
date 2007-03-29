from django.conf import settings
from django.core import cache as django_cache
from django.http import HttpRequest, HttpResponse

from channelguide import cache as channelguide_cache
from channelguide import util
import time
from channelguide.testframework import TestCase

class CacheTest(TestCase):
    def setUp(self):
        TestCase.setUp(self)
        self.change_setting_for_test("DISABLE_CACHE", False)
        self.middleware = channelguide_cache.CacheMiddleware()
        time.sleep(1) 
        # hack because we may have called memcached.flush_all recently.
        # Because memcached has a resolution of 1 second, we need this to make
        # sure flush_all goes through.

    def tearDown(self):
        channelguide_cache.memcache_client.flush_all()
        TestCase.tearDown(self)

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

    def test_cache(self):
        path = self.rand_path()
        self.assert_(not self.is_request_cached(path))
        self.assert_(self.is_request_cached(path))
        self.assert_(not self.is_request_cached(path, 'foo=bar'))
        self.assert_(self.is_request_cached(path, 'foo=bar'))

    def test_expire(self):
        path = self.rand_path()
        self.make_request_cached(path)
        channelguide_cache.clear_cache()
        self.assert_(not self.is_request_cached(path))

    def test_default_cache_control(self):
        path = self.rand_path()
        request = self.make_request(path)
        self.middleware.process_request(request)
        response = self.process_response(request)
        self.assertEquals(response.headers['Cache-Control'], 'max-age=0')

    def test_manual_cache_control(self):
        path = self.rand_path()
        request = self.make_request(path)
        self.middleware.process_request(request)
        response = self.make_response()
        channelguide_cache.cache_externally_for(response, 123)
        self.process_response_middleware(request, response)
        self.assertEquals(response.headers['Cache-Control'], 'max-age=123')

    def test_middleware_when_cached(self):
        path = self.rand_path()
        request = self.make_request(path)
        self.middleware.process_request(request)
        self.middleware.process_response(request, self.make_response())
        request = self.make_request(path)
        cached_request = self.middleware.process_request(request)
        self.process_response(request)

    def test_expire_on_object_change(self):
        path = self.rand_path()
        user = self.make_user("kelly")
        channel = self.make_channel(user)
        self.save_to_db(channel)
        time.sleep(1) # see above for why
        self.make_request_cached(path)
        channel.name = "NEW ONE"
        self.db_session.flush()
        self.assert_(not self.is_request_cached(path))
