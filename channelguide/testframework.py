# Copyright (c) 2008 Participatory Culture Foundation
# See LICENSE for details.

import logging
import os
import shutil
import unittest
import traceback

from django.conf import settings
from django.core import signals
from django.http import HttpRequest, HttpResponse
from django.test.client import Client

from channelguide import db
from channelguide import util

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

class TestCase(unittest.TestCase):
    """Base class for the channelguide unittests."""

    def setUp(self):
        from channelguide.guide.models import Language
        setup_test_environment()
        db.pool.timeout = 0.01
        self.connection = db.connect()
        self.log_filter = TestLogFilter()
        self.language = Language("booyarish")
        self.save_to_db(self.language)
        util.emailer = self.catch_email
        self.emails = []
        settings.DISABLE_CACHE = True
        settings.USE_S3 = False
        settings.BASE_URL_FULL = 'http://testserver/'
        self.client = Client()
        self.changed_settings = []

    def change_setting_for_test(self, name, value):
        self.changed_settings.append((name, getattr(settings, name)))
        setattr(settings, name, value)

    def catch_email(self, title, body, email_from, recipient_list):
        self.emails.append({'title': title, 'body': body, 
            'email_from': email_from, 'recipient_list': recipient_list})
        self.sanity_check_email(self.emails[-1])

    def email_recipients(self):
        recipients = []
        for email in self.emails:
            recipients.extend(email['recipient_list'])
        return recipients

    def sanity_check_email(self, email):
        self.assert_(isinstance(email['email_from'], (str, unicode)),
                '%r is not a string' % (email['email_from'],))
        self.assertEquals(type(email['recipient_list']), list)

    def tearDown(self):
        try:
            self.resume_logging()
            util.emailer = None
            self.connection.commit()
            self.connection.close()
            if os.path.exists(settings.MEDIA_ROOT):
                shutil.rmtree(settings.MEDIA_ROOT)
            if os.path.exists(settings.IMAGE_DOWNLOAD_CACHE_DIR):
                shutil.rmtree(settings.IMAGE_DOWNLOAD_CACHE_DIR)
            for name, oldvalue in self.changed_settings:
                setattr(settings, name, oldvalue)
            signals.request_finished.send(None)
            # The above line should close any open request connections
            for connection in db.pool.free:
                connection.close_raw_connection()
            db.pool.free = []
            for connection in list(db.pool.used):
                connection.destroy()
            db.pool.used = set()
        finally:
            teardown_test_environment()

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
        self.assertRedirect(response, 'accounts/login')

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
                    util.make_absolute_url('accounts/login'))
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

    def all_tables(self):
        rows = self.connection.execute("SHOW TABLES;")
        return [row[0] for row in rows]

    def delete_all_tables(self):
        all_tables = set(self.all_tables())
        # this is a little tricky because of foreign key constraints.  The
        # stragegy is just brute force
        while all_tables:
            start_len = len(all_tables)
            for table in list(all_tables):
                try:
                    self.connection.execute("DELETE FROM %s" % table)
                except:
                    pass
                else:
                    all_tables.remove(table)
            if len(all_tables) == start_len:
                raise AssertionError("Can't delete any tables")


    def save_to_db(self, *objects):
        for object in objects:
            object.save(self.connection)
        self.connection.commit()

    def refresh_record(self, record, *joins):
        self.refresh_connection()
        pk = self.rowid = record.primary_key_values()
        retval = record.__class__.get(self.connection, pk, join=joins)
        return retval

    def debug_response_context(self, context):
        for dict in context.dicts:
            for key, value in dict.items():
                print '%s => %s' % (key, value)

    def refresh_connection(self):
        self.connection.commit()

    def make_user(self, username, password='password', role='U'):
        from channelguide.guide.models import User
        user = User(username, password, "%s@test.test" % username)
        user.role = role
        self.save_to_db(user)
        return user

    def make_channel(self, owner, state='N', keep_download=False):
        from channelguide.guide.models import Channel
        channel = Channel()
        channel.state = state
        channel.language = self.language
        channel.owner = owner
        channel.name = u"My Channel \u1111"
        channel.url = "http://myblog.com/videos/rss/" 
        channel.url += util.random_string(20)
        channel.website_url = "http://myblog.com/"
        channel.publisher = "TestVision@TestVision.com"
        channel.description = u"lots of stuff \u3333"
        if not keep_download:
            channel.download_feed = lambda: None # don't try to download feed
        self.save_to_db(channel)
        return channel

    def login(self, username, password='password'):
        data = {'username': unicode(username), 'password': password,
                'which-form': 'login' }
        return self.client.post('/accounts/login', data)

    def logout(self):
        return self.client.get('/accounts/logout')

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
        try:
            signals.request_finished.send(None)
        except AttributeError:
            # this is for backwards-compatibility with pre-Django 1.0
            from django.dispatch import dispatcher
            dispatcher.send(signals.request_finished)
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

def setup_test_environment():
    settings.OLD_DATABASE_NAME = settings.DATABASE_NAME
    if not settings.DATABASE_NAME.startswith('test_'):
        settings.DATABASE_NAME = 'test_' + settings.DATABASE_NAME
    reload(db)
    import django.test.utils
    try:
        db.dbinfo.create_database()
    except:
        db.dbinfo.drop_database()
        db.dbinfo.create_database()
    db.syncdb()
    django.test.utils.setup_test_environment()

def teardown_test_environment():
    import django.test.utils
    django.test.utils.teardown_test_environment()
    db.dbinfo.drop_database()
    settings.DATABASE_NAME = settings.OLD_DATABASE_NAME

