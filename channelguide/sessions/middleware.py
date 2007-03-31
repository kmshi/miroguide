import logging
import traceback

from django.conf import settings
from django.contrib.sessions.middleware import SessionWrapper
from django.utils.cache import patch_vary_headers

from models import Session
from util import get_session_from_key, make_new_session_key
from channelguide import util
from channelguide.db import dbutil

class CGSessionWrapper(SessionWrapper):
    def __init__(self, request):
        cookie_name = settings.SESSION_COOKIE_NAME
        self.session_key = request.COOKIES.get(cookie_name, None)
        self.db_session = request.db_session
        self.modified = False

    def _get_session(self):
        # Lazily loads session from storage.
        try:
            return self._session_cache
        except AttributeError:
            session = get_session_from_key(self.db_session, self.session_key)
            try:
                self._session_cache = session.get_data()
            except:
                logging.warn("Error getting session data\n" +
                        traceback.format_exc())
                session.set_data({})
                self._session_cache = {}
            return self._session_cache
    _session = property(_get_session)

    def change_session_key(self):
        self._get_session() # causes _session_cache to be loaded
        if self.session_key is not None:
            old_session = self.db_session.get(Session, self.session_key)
            if old_session is not None:
                self.db_session.delete(old_session)
        self.session_key = make_new_session_key(self.db_session)
        self.modified = True

class SessionMiddleware(object):
    """Adds a session object to each request."""

    def process_request(self, request):
        request.session = CGSessionWrapper(request)

    def process_response(self, request, response):
        # If request.session was modified, or if response.session was set, save
        # those changes and set a session cookie.
        patch_vary_headers(response, ('Cookie',))
        if hasattr(request, 'session') and request.session.modified:
            db_session = request.db_session
            session = get_session_from_key(db_session,
                    request.session.session_key)
            session.set_data(request.session._session)
            session.update_expire_date()
            if session.session_key is None:
                session.session_key = make_new_session_key(db_session)
                db_session.save(session)
            util.set_cookie(response, settings.SESSION_COOKIE_NAME,
                    session.session_key, settings.SESSION_COOKIE_AGE)
        return response
