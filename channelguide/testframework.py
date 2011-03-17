# Copyright (c) 2008 Participatory Culture Foundation
# See LICENSE for details.

import logging
import os
import traceback

from django.conf import settings
from django.core import signals, mail
from django.contrib.auth.models import User, Group
from django.http import HttpRequest, HttpResponse
from django import test

from channelguide import util

def test_data_path(filename):
    return os.path.abspath(os.path.join(os.path.dirname(__file__),
                                        'testdata',
                                        filename))

def test_data_url(filename):
    return 'file://' + test_data_path(filename)

def clear_cache():
    from django.core.cache import cache
    if hasattr(cache, '_cache'):
        if isinstance(cache._cache, dict):
            cache._cache = {}
            cache._expire_info = {}

class TestLogFilter(logging.Filter):
    def __init__(self):
        logging.Filter.__init__(self)
        self.records_seen = []

    def filter(self, record):
        self.records_seen.append(record)
        return 0

    def get_level_counts(self):
        counts = {}
        for rec in self.records_seen:
            counts[rec.levelno] = counts.get(rec.levelno, 0) + 1
        return counts

    def reset(self):
        self.records_seen = []

class TestCase(test.TestCase):
    """Base class for the channelguide unittests."""

    def setUp(self):
        test.TestCase.setUp(self)
        from channelguide.labels.models import Language
        self.log_filter = TestLogFilter()
        self.language = Language(name=u"booyarish")
        self.language.save()
        settings.USE_S3 = False
        settings.BASE_URL_FULL = 'http://testserver/'
        self.changed_settings = []
        clear_cache()

    def change_setting_for_test(self, name, value):
        self.changed_settings.append((name, getattr(settings, name)))
        setattr(settings, name, value)

    def email_recipients(self):
        recipients = []
        for email in mail.outbox:
            recipients.extend(email.recipients())
        return recipients

    def tearDown(self):
        test.TestCase.tearDown(self)
        self.resume_logging()
        #if os.path.exists(settings.MEDIA_ROOT):
        #    shutil.rmtree(settings.MEDIA_ROOT)
        #if os.path.exists(settings.IMAGE_DOWNLOAD_CACHE_DIR):
        #    shutil.rmtree(settings.IMAGE_DOWNLOAD_CACHE_DIR)
        for name, oldvalue in self.changed_settings:
            setattr(settings, name, oldvalue)
        signals.request_finished.send(None)


    def assertSameSet(self, iterable1, iterable2):
        self.assertEquals(set(iterable1), set(iterable2))
        self.assertEquals(len(iterable1), len(iterable2))

    def assertRedirect(self, response, redirect_url):
        """
        Asserts that the given response is a redirect to the given URL.
        """
        self.assertEquals(response.status_code, 302,
                "Not redirected:\nHeader: %i\nContent: %s" % (
                    response.status_code, response.content))
        location_path = response['Location'].split('?')[0]
        self.assertEqual(location_path, util.make_absolute_url(redirect_url))

    def assertLoginRedirect(self, response_or_url, login_as=None):
        if isinstance(response_or_url, basestring):
            response = self.get_page(response_or_url, login_as)
        else:
            response = response_or_url
        self.assertRedirect(response, settings.LOGIN_URL)

    def assertCanAccess(self, response_or_url, login_as=None):
        if isinstance(response_or_url, basestring):
            response = self.get_page(response_or_url, login_as)
        else:
            response = response_or_url
        if response.status_code == 200:
            return
        elif response.status_code == 302:
            location_path = response['Location'].split('?')[0]
            self.assertNotEquals(location_path,
                    util.make_absolute_url(settings.LOGIN_URL),
                                 '%s could not access %s' % (
                    login_as, response_or_url))
        else:
            raise AssertionError("Bad status code: %s" % response.status_code)

    def check_page_access(self, user, url, should_access):
        self.login(user)
        if should_access:
            self.assertCanAccess(url)
        else:
            self.assertLoginRedirect(url)

    def pause_logging(self):
        logging.getLogger('').addFilter(self.log_filter)

    def check_logging(self, infos=0, warnings=0, errors=0):
        counts = self.log_filter.get_level_counts()
        self.assertEquals(infos, counts.get(logging.INFO, 0))
        self.assertEquals(warnings, counts.get(logging.WARN, 0))
        self.assertEquals(errors, counts.get(logging.ERROR, 0))

    def resume_logging(self):
        logging.getLogger('').removeFilter(self.log_filter)
        self.log_filter.reset()

    def debug_response_context(self, context):
        for dict in context.dicts:
            for key, value in dict.items():
                print '%s => %s' % (key, value)

    def make_user(self, username, password='password', group=None):
        user = User.objects.create_user(username,
                                        "%s@test.test" % username,
                                        password)
        if group is not None:
            if isinstance(group, (str, unicode)):
                group = [group]
            for name in group:
                obj = Group.objects.get(name=name)
                user.groups.add(obj)
        return user

    def make_channel(self, owner, state='N', keep_download=False):
        from channelguide.channels.models import Channel
        channel = Channel.objects.create(
            state=state,
            language=self.language,
            owner=owner,
            name=u"My Channel \u1111",
            url="http://myblog.com/videos/rss/" + util.random_string(20),
            website_url="http://myblog.com/",
            publisher="TestVision@TestVision.com",
            description=u"lots of stuff \u3333"
        )
        if not keep_download:
            channel.download_feed = lambda: None # don't try to download feed
        return channel

    def login(self, username, password='password'):
        data = {'username': unicode(username), 'password': password,
                'which-form': 'login' }
        return self.client.post(settings.LOGIN_URL, data)

    def logout(self):
        return self.client.get(settings.LOGOUT_URL)

    def get_traceback_from_response(self, response):
        if type(response.context) != list:
            contexts = [response.context]
        else:
            contexts = response.context
        for context in contexts:
            if 'frames' in context:
                return context['frames'][0]['tb']

    def check_response(self, response):
        if response.status_code == 500:
            file('/tmp/error.html', 'w').write(response.content)
            if isinstance(response.context, list):
                context = response.context[-1]
            else:
                context = response.context
            try:
                type = globals()[context['exception_type']]
            except KeyError:
                type = Exception
            trace = traceback.format_exception(type,
                    context['exception_value'],
                    self.get_traceback_from_response(response))
            trace = '\n'.join(trace)
            raise ValueError("Got 500 status code.  Traceback:\n\n%s" % trace)
        elif response.status_code == 404:
            if 'Django tried these URL patterns' in str(response):
                raise ValueError("Got 404 status code, no url conf match")
            return response
        else:
            return response

    def get_page(self, path, login_as=None, data=None):
        if login_as is not None:
            self.login(login_as)
        if data is None:
            return self.check_response(self.client.get(path))
        else:
            return self.check_response(self.client.get(path, data))

    def post_data(self, path, data, login_as=None):
        if login_as is not None:
            self.login(login_as)
        return self.check_response(self.client.post(path, data))

    def get_middleware_objects(self):
        objects = []
        for middleware in settings.MIDDLEWARE_CLASSES:
            mod_name, class_name = middleware.rsplit('.', 1)
            mod = util.import_last_component(mod_name)
            objects.append(getattr(mod, class_name)())
        return objects

    def process_request(self, cookies_from=None, request=None):
        if request is None:
            request = HttpRequest()
        if cookies_from:
            for key, cookie in cookies_from.items():
                try:
                    request.COOKIES[key] = cookie.value
                except AttributeError: # probably a plain dict
                    request.COOKIES[key] = cookie
        for obj in self.get_middleware_objects():
            if hasattr(obj, 'process_request'):
                obj.process_request(request)
        return request

    def process_response(self, request):
        response = HttpResponse()
        self.process_response_middleware(request, response)
        signals.request_finished.send(sender=self.request.__class__,
                                      instance=self.request)
        return response

    def process_response_middleware(self, request, response):
        for obj in reversed(self.get_middleware_objects()):
            if hasattr(obj, 'process_response'):
                response = obj.process_response(request, response)

    def process_exception(self, request, exception):
        for obj in reversed(self.get_middleware_objects()):
            if hasattr(obj, 'process_exception'):
                response = obj.process_exception(request, exception)
                if response:
                    return response
        return self.process_response(request)
