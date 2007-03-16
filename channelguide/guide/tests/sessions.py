from datetime import datetime, timedelta

from django.http import HttpRequest, HttpResponse
from django.conf import settings
from django.http import HttpRequest
from sqlalchemy import create_session

from channelguide.testframework import TestCase
from channelguide import db
from channelguide.db.middleware import DBMiddleware
from channelguide.sessions.middleware import SessionMiddleware
from channelguide.sessions.models import Session

class SessionTest(TestCase):
    def test_session_exists(self):
        request = self.process_request()
        self.assert_(hasattr(request, 'session'))

    def test_session_save(self):
        request = self.process_request()
        request.session['foo'] = 'bar'
        response = self.process_response(request)
        request = self.process_request(cookies_from=response.cookies)
        self.assertEquals(request.session.get('foo'), 'bar')

    def test_session_expire(self):
        request = self.process_request()
        request.session['foo'] = 'bar'
        response = self.process_response(request)
        session_key = response.cookies[settings.SESSION_COOKIE_NAME].value
        self.reopen_connection()
        session = self.db_session.get(Session, session_key)
        session.expires = datetime.now()
        self.db_session.update(session)
        self.db_session.flush()
        request = self.process_request(cookies_from=response.cookies)
        self.assertEquals(request.session.get('foo'), None)

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
        self.reopen_connection()
        session = self.db_session.get(Session, session_key)
        session.data = 'BOOYA---12312b'
        self.save_to_db(session)
        self.pause_logging()
        request = self.process_request(cookies_from=response.cookies)
        self.check_logging(warnings=1)
        self.resume_logging()
        self.assertEquals(request.session.items(), [])
