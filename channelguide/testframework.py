import logging
import os
import shutil
import unittest
import traceback

from django.conf import settings
from django.http import HttpRequest, HttpResponse
from django.test.client import Client
from sqlalchemy import BoundMetaData, Table, create_session

from channelguide import db, cache
from channelguide.db import version
from channelguide import util

def table_iterator():
    table_names = set([row[0] for row in db.engine.execute("SHOW TABLES")])
    meta = BoundMetaData(db.engine)
    for name in table_names:
        Table(name, meta, autoload=True)
    return meta.table_iterator()

def drop_tables():
    for table in table_iterator():
        table.drop()

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
        self.connection = db.connect()
        self.db_session = create_session(bind_to=self.connection)
        self.log_filter = TestLogFilter()
        self.language = Language("booyarish")
        self.db_session.save(self.language)
        self.db_session.flush()
        self.starting_db_version = version.get_version(self.connection)
        util.emailer = self.catch_email
        self.emails = []
        settings.DISABLE_CACHE = True
        self.client = Client()
        self.changed_settings = []

    def change_setting_for_test(name, value):
        self.changed_settings.append((name, getattr(settings, name)))
        setattr(settings, name, value)

    def catch_email(self, title, body, email_from, recipient_list):
        self.emails.append({'title': title, 'body': body, 
            'email_from': email_from, 'recipient_list': recipient_list})
        self.sanity_check_email(self.emails[-1])

    def sanity_check_email(self, email):
        self.assertEquals(type(email['email_from']), str)
        self.assertEquals(type(email['recipient_list']), list)

    def tearDown(self):
        self.resume_logging()
        util.emailer = None
        self.delete_all_tables()
        self.connection.execute("INSERT INTO cg_db_version values(%s)",
                self.starting_db_version)
        self.connection.close()
        if os.path.exists(settings.MEDIA_ROOT):
            shutil.rmtree(settings.MEDIA_ROOT)
        if os.path.exists(settings.IMAGE_DOWNLOAD_CACHE_DIR):
            shutil.rmtree(settings.IMAGE_DOWNLOAD_CACHE_DIR)
        for name, oldvalue in self.changed_settings:
            setattr(settings, name, oldvalue)

    def assertSameSet(self, iterable1, iterable2):
        self.assertEquals(set(iterable1), set(iterable2))

    def assertRedirect(self, response, redirect_url):
        self.assertEquals(response.status_code, 302)
        location_path = response.headers['Location'].split('?')[0]
        self.assertEqual(location_path, util.make_absolute_url(redirect_url))

    def assertLoginRedirect(self, response_or_url, login_as=None):
        if type(response_or_url) is str:
            response = self.get_page(response_or_url, login_as)
        else:
            response = response_or_url
        self.assertRedirect(response, 'accounts/login')

    def assertCanAccess(self, response_or_url, login_as=None):
        if type(response_or_url) is str:
            response = self.get_page(response_or_url, login_as)
        else:
            response = response_or_url
        self.assertEquals(response.status_code, 200)

    def check_page_access(self, user, url, should_access):
        self.login(user)
        if should_access:
            self.assertCanAccess(url)
        else:
            self.assertLoginRedirect(url)

    def reopen_connection(self):
        self.connection.close()
        self.connection = db.connect()
        self.db_session = create_session(bind_to=self.connection)

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

    def delete_all_tables(self, use_drop=False):
        for table in table_iterator():
            table.delete().execute()

    def save_to_db(self, *objects):
        for obj in objects:
            self.db_session.save(obj)
        self.db_session.flush(objects)

    def query(self, class_):
        return self.db_session.query(class_)

    def refresh_connection(self):
        self.connection.execute("COMMIT")

    def refresh_db_object(self, obj):
        self.refresh_connection()
        self.db_session.refresh(obj)

    def make_user(self, username, password='password', role='U'):
        from channelguide.guide.models import User
        user = User(username, password)
        user.role = role
        user.email = "%s@pculture.org" % username
        self.save_to_db(user)
        return user

    def make_channel(self, owner):
        from channelguide.guide.models import Channel
        channel = Channel()
        channel.language = self.language
        channel.owner = owner
        channel.name = "My Channel"
        channel.url = "http://myblog.com/videos/rss/" 
        channel.url += util.random_string(20)
        channel.website_url = "http://myblog.com/"
        channel.publisher = "TestVision"
        channel.short_description = "stuff"
        channel.description = "lots of stuff"
        self.save_to_db(channel)
        return channel

    def login(self, username, password='password'):
        data = {'username': username, 'password': password,
                'which-form': 'login' }
        return self.client.post('/accounts/login', data)

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
            if isinstance(response.context, list):
                context = response.context[0]
            else:
                context = response.context
            trace = traceback.format_exception(
                    context['exception_value'],
                    context['exception_type'],
                    self.get_traceback_from_response(response))
            trace = '\n'.join(trace)
            raise ValueError("Got 500 status code.  Traceback:\n\n%s" % trace)
        elif response.status_code == 404:
            if 'Django tried these URL patterns' in str(response):
                raise ValueError("Got 404 status code, no url conf match")
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
    
    def process_request(self, cookies_from=None):
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
