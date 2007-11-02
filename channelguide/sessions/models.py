from datetime import datetime, timedelta
import time

from django.conf import settings
from sqlhelper import NotFoundError
from channelguide.cache import client

class Session(object):

    def __init__(self):
        self.set_data({})
        self.session_key = None
        self.update_expire_date()

    def set_data(self, dict):
        self.data = dict

    def get_data(self):
        if not isinstance(self.data, dict):
            raise Exception()
        return self.data

    def update_expire_date(self):
        age_timedelta = timedelta(seconds=settings.SESSION_COOKIE_AGE)
        self.expires = datetime.now() + age_timedelta

    @staticmethod
    def _cache_key(session_key):
        return 'Session:' + session_key

    @classmethod
    def get(cls, connection, session_key):
        obj = client.get(cls._cache_key(session_key))
        if obj is None:
            raise NotFoundError
        return obj

    def save(self, connection):
        expires = time.mktime(self.expires.timetuple())
        key = self._cache_key(self.session_key)
        client.set(key, self, expires)

    def delete(self, connection):
        if self.session_key is not None:
            client.delete(self._cache_key(self.session_key))

    delete_if_exists = delete
