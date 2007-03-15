import logging
import traceback

from django.conf import settings
from django.contrib.sessions.middleware import SessionWrapper
from django.utils.cache import patch_vary_headers

from models import Session
from channelguide import util

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
            session = Session.get_from_key(self.db_session, self.session_key)
            try:
                self._session_cache = session.get_data()
            except:
                logging.warn("Error getting session data\n" +
                        traceback.format_exc())
                session.set_data({})
                self.db_session.save(session)
                self._session_cache = {}
            return self._session_cache
    _session = property(_get_session)

class SessionMiddleware(object):
    """Adds a session object to each request."""

    def process_request(self, request):
        request.session = CGSessionWrapper(request)

    def process_response(self, request, response):
        # If request.session was modified, or if response.session was set, save
        # those changes and set a session cookie.
        patch_vary_headers(response, ('Cookie',))
        if request.session.modified:
            session = Session.get_from_key(request.db_session, 
                    request.session.session_key)
            session.set_data(request.session._session)
            session.update_expire_date()
            util.save_if_new(request.db_session, session)
            util.set_cookie(response, settings.SESSION_COOKIE_NAME,
                    session.session_key, settings.SESSION_COOKIE_AGE)
        return response
