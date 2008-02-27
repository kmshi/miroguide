# Copyright (c) 2008 Participatory Culture Foundation
# See LICENSE for details.

from datetime import datetime, timedelta

from django.http import HttpRequest, HttpResponse
from django.conf import settings

from channelguide.testframework import TestCase
from channelguide.db.middleware import DBMiddleware
from channelguide.sessions.middleware import SessionMiddleware
from channelguide.sessions.models import Session

class SessionTest(TestCase):
    def test_session_exists(self):
        request = self.process_request()
        self.assert_(hasattr(request, 'session'))
        self.process_response(request)

    def test_session_save(self):
        request = self.process_request()
        request.session['foo'] = 'bar'
        response = self.process_response(request)
        request = self.process_request(cookies_from=response.cookies)
        self.assertEquals(request.session.get('foo'), 'bar')
        self.process_response(request)

    def test_session_expire(self):
        request = self.process_request()
        request.session['foo'] = 'bar'
        response = self.process_response(request)
        session_key = response.cookies[settings.SESSION_COOKIE_NAME].value
        self.connection.commit()
        session = Session.get(self.connection, session_key)
        session.expires = datetime.now()
        session.save(self.connection)
        self.connection.commit()
        request = self.process_request(cookies_from=response.cookies)
        self.assertEquals(request.session.get('foo'), None)
        self.process_response(request)

    def test_invalid_session_key(self):
        request = HttpRequest()
        request.COOKIES[settings.SESSION_COOKIE_NAME] = 'foo'
        DBMiddleware().process_request(request)
        SessionMiddleware().process_request(request)
        self.assertEquals(request.session.items(), [])

    def test_session_data_corrupt(self):
        request = self.process_request()
        request.session['foo'] = 'bar'
        response = self.process_response(request)
        session_key = response.cookies[settings.SESSION_COOKIE_NAME].value
        self.connection.commit()
        session = Session.get(self.connection, session_key)
        # remove the non-pickled data, so that it has to be loaded
        del session._unencoded_data
        session.data = 'BOOYA---12312b'
        session.save(self.connection)
        self.refresh_connection()
        self.pause_logging()
        request = self.process_request(cookies_from=response.cookies)
        self.check_logging(warnings=1)
        self.resume_logging()
        self.assertEquals(request.session.items(), [])
        self.process_response(request)

    def test_change_session_key(self):
        request = self.process_request()
        request.session['foo'] = 'bar'
        response = self.process_response(request)
        old_key = request.session.session_key
        request = self.process_request(cookies_from=response.cookies)
        request.session.change_session_key()
        response = self.process_response(request)
        new_key = request.session.session_key
        self.connection.commit()
        self.assertRaises(LookupError, Session.get, self.connection, old_key)
        session = Session.get(self.connection, new_key)

    def test_delete_ignores_missing_session_key(self):
        Session().delete(self.connection)
