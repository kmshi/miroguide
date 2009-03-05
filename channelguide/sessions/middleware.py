# Copyright (c) 2008 Participatory Culture Foundation
# See LICENSE for details.

import logging
import traceback

from django.conf import settings
from django.utils.cache import patch_vary_headers

from models import Session
from util import get_session_from_key, make_new_session_key
from channelguide import util

class CGSessionWrapper(object):
    def __init__(self, request):
        cookie_name = settings.SESSION_COOKIE_NAME
        self.session_key = request.COOKIES.get(cookie_name, None)
        self.connection = request.connection
        self.modified = False
        self.session_loaded = False

    def load_session(self):
        if self.session_loaded:
            return
        session = get_session_from_key(self.connection, self.session_key)
        try:
            self._session_data = session.get_data()
        except:
            logging.warn("Error getting session data\n" +
                    traceback.format_exc())
            session.set_data({})
            self._session_data = {}
        self._record = session
        self.session_loaded = True

    def _get_session(self):
        self.load_session()
        return self._session_data
    _session = property(_get_session)

    def make_new_session_key(self):
        self.session_key = make_new_session_key(self.connection)
        self._record.session_key = self.session_key

    def change_session_key(self):
        self.load_session()
        self._record.delete_if_exists(self.connection)
        self.make_new_session_key()
        self.modified = True

    def save(self):
        session = self._record
        self._record.set_data(self._session_data)
        self._record.update_expire_date()
        if self._record.session_key is None:
            self.make_new_session_key()
        self._record.save(self.connection)

    def __contains__(self, key):
        return key in self._session

    def __getitem__(self, key):
        return self._session[key]

    def __setitem__(self, key, value):
        self._session[key] = value
        self.modified = True

    def __delitem__(self, key):
        del self._session[key]
        self.modified = True

    def keys(self):
        return self._session.keys()

    def items(self):
        return self._session.items()

    def get(self, key, default=None):
        return self._session.get(key, default)

    def pop(self, key, *args):
        self.modified = True
        return self._session.pop(key, *args)

    def add_notification(self, title, body):
        if 'notifications' not in self:
            self['notifications'] = []
        self['notifications'].append((title, body))
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
            request.session.save()
            util.set_cookie(response, settings.SESSION_COOKIE_NAME,
                    request.session.session_key, settings.SESSION_COOKIE_AGE)
        return response
