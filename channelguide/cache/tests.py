from channelguide.testframework import TestCase, clear_cache
from datetime import datetime

from django.conf import settings
from django.http import HttpRequest, HttpResponse
from django.contrib.auth.models import AnonymousUser
from django.contrib.sessions.models import Session

from channelguide import util
from channelguide.cache import middleware

class CacheTestBase(TestCase):

    def make_request(self, path, query=None):
        request = HttpRequest()
        request.method = "GET"
        request.path = path
        request.user = AnonymousUser()
        request.session = {}
        request.LANGUAGE_CODE = settings.LANGUAGE_CODE
        request.META['QUERY_STRING'] = query
        return request

    def make_response(self):
        response = HttpResponse("Hello World")
        response.status_code = 200
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
        request.LANGUAGE_CODE = settings.LANGUAGE_CODE
        if self.middleware.process_request(request) is None:
            self.middleware.process_response(request, self.make_response())
        self.assert_(self.is_request_cached(path, query))

class UserCacheMiddlewareTest(CacheTestBase):
    def setUp(self):
        CacheTestBase.setUp(self)
        self.middleware = middleware.UserCacheMiddleware()

    def test_cache(self):
        path = self.rand_path()
        self.assert_(not self.is_request_cached(path))
        self.assert_(self.is_request_cached(path))
        self.assert_(not self.is_request_cached(path, 'foo=bar'))
        self.assert_(self.is_request_cached(path, 'foo=bar'))

    def test_expire(self):
        path = self.rand_path()
        self.make_request_cached(path)
        clear_cache()
        self.assert_(not self.is_request_cached(path))

    def test_expire_on_object_change(self):
        user = self.make_user("kelly")
        channel = self.make_channel(user)
        path = '/channels/popular'
        channel.save()
        self.make_request_cached(path)
        channel.name = "NEW ONE"
        channel.save()
        self.assert_(not self.is_request_cached(path))

    def test_session_change_doesnt_expire_cache(self):
        path = self.rand_path()
        self.make_request_cached(path)
        Session.objects.save('1231123123',
                             {'foo': 'bar'},
                             datetime.now())
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

        self.assert_('userbobby' not in anon_page.content)
        self.assert_('userbobby' not in kelly_page.content)
        self.assert_('userbobby' in bobby_page.content)
        self.assert_('userbobby' not in anon_page.content)

        self.assert_('userkelly' not in anon_page.content)
        self.assert_('userkelly' in kelly_page.content)
        self.assert_('userkelly' not in bobby_page.content)
        self.assert_('userkelly' not in anon_page.content)


class SiteHidingCacheMiddlewareTest(CacheTestBase):
    def setUp(self):
        CacheTestBase.setUp(self)
        self.middleware = middleware.SiteHidingCacheMiddleware()

    def make_request_with_useragent(self, path, query=None, user_agent=None):
        request = self.make_request(path, query)
        if user_agent:
            request.META['HTTP_USER_AGENT'] = user_agent
        return request

    def test_old_miro(self):
        request = self.make_request_with_useragent('/',
                                                  user_agent='Miro/1.2.8')
        self.assertEqual(self.middleware.process_request(request), None)
        self.middleware.process_response(request, self.make_response())
        request = self.make_request_with_useragent('/',
                                                  user_agent='Miro/1.0')
        self.assertNotEqual(self.middleware.process_request(request), None)
        request = self.make_request_with_useragent('/',
                                                  user_agent='Miro/2.0.2')
        self.assertEqual(self.middleware.process_request(request), None)

    def test_linux_miro(self):
        request = self.make_request_with_useragent(
            '/',
            user_agent='Miro/2.0 (X11; Ubuntu Linux)')
        self.assertEqual(self.middleware.process_request(request), None)
        self.middleware.process_response(request, self.make_response())
        request = self.make_request_with_useragent(
            '/',
            user_agent='Miro/2.0 (X11; Ubuntu Linux)')
        self.assertNotEqual(self.middleware.process_request(request), None)
        request = self.make_request_with_useragent('/',
                                                  user_agent='Miro/2.0.2')
        self.assertEqual(self.middleware.process_request(request), None)


class ChannelCacheTest(CacheTestBase):

    def setUp(self):
        TestCase.setUp(self)
        self.owner = self.make_user('owner')
        self.regular = self.make_user('regular')
        self.regular.get_profile().approved = True
        self.regular.get_profile().save()
        self.mod = self.make_user('mod', group='cg_moderator')
        self.super = self.make_user('super', group=['cg_moderator',
                                                    'cg_supermoderator'])
        self.channel = self.make_channel(self.owner, state='A')

    def check_response_cached(self, response, was_cached):
        if was_cached:
            self.assertTrue(
                getattr(response, '_cache_hit', False),
                '%s was not cached' % response.request['PATH_INFO'])
        else:
            self.assertFalse(hasattr(response, '_cache_hit'),
                             '%s was cached' % response.request['PATH_INFO'])

    def get_renderings(self):
        url = self.channel.get_url()
        regular_render = self.get_page(url, login_as=self.regular).content
        mod_render = self.get_page(url, login_as=self.mod).content
        super_render = self.get_page(url, login_as=self.super).content
        owner_render = self.get_page(url, login_as=self.owner).content
        return (regular_render, mod_render, super_render, owner_render)

    def test_channel_renders_differently_for_each_class(self):
        """
        The channel page should render differently for each class of user,
        regular, moderator, owner, and super-mod.
        """
        (regular_render, mod_render, super_render,
                owner_render) = self.get_renderings()
        self.failIfEqual(regular_render, mod_render)
        self.failIfEqual(regular_render, super_render)
        self.failIfEqual(regular_render, owner_render)
        self.failIfEqual(mod_render, super_render)
        self.failIfEqual(mod_render, owner_render)
        self.failIfEqual(super_render, owner_render)

    def test_updating_channel_refreshes_page(self):
        """
        Changing the channel record should refresh the page.
        """
        url = self.channel.get_url()
        for user in (self.regular, self.mod, self.super, self.owner):
            self.check_response_cached(self.get_page(url,
                                                     login_as=user), False)
            self.check_response_cached(self.get_page(url,
                                                     login_as=user), True)
        (regular_render, mod_render, super_render,
                owner_render) = self.get_renderings()
        self.channel.description = 'Hello World!'
        self.channel.save()
        for user in (self.regular, self.mod, self.super, self.owner):
            self.check_response_cached(self.get_page(url,
                                                     login_as=user), False)
            self.check_response_cached(self.get_page(url,
                                                     login_as=user), True)

    def test_changing_other_channel_doesnt_clear_cache(self):
        """
        Updating a different channel should not clear the cache for other
        channels.
        """
        url = self.channel.get_url()
        for user in (self.regular, self.mod, self.super, self.owner):
            self.check_response_cached(self.get_page(url,
                                                     login_as=user), False)
            self.check_response_cached(self.get_page(url,
                                                     login_as=user), True)
        channel2 = self.make_channel(self.owner, state='A')
        channel2.description = 'Hello World!'
        channel2.save()
        for user in (self.regular, self.mod, self.super, self.owner):
            self.check_response_cached(self.get_page(url,
                                                     login_as=user), True)
