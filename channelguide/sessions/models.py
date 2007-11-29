from datetime import datetime, timedelta
import time
try:
    import cPickle as pickle
except ImportError:
    import pickle

from django.conf import settings
from sqlhelper.orm import Table, columns, Record
from sqlhelper import NotFoundError
from channelguide.cache import client

session_table = Table('cg_session',
        columns.String('session_key', 40, primary_key=True),
        columns.String('data'),
        columns.DateTime('expires'))

class Session(Record):

    table = session_table

    def __init__(self):
        self.set_data({})
        self.session_key = None
        self.update_expire_date()

    def set_data(self, dict):
        self._unencoded_data = dict
        self.data = pickle.dumps(dict)

    def get_data(self):
        if self._unencoded_data is None:
            self._unencoded_data = pickle.loads(self.data.encode('charmap'))
        return self._unencoded_data

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
            obj = super(Session, cls).get(connection, session_key)
            obj._unencoded_data = None
            obj.save(None)
        return obj

    def save(self, connection):
        if connection is not None:
            super(Session, self).save(connection)
        expires = time.mktime(self.expires.timetuple())
        key = self._cache_key(self.session_key)
        client.set(key, self, expires)

    def delete(self, connection):
        if self.session_key is not None:
            super(Session, self).delete(connection)
            client.delete(self._cache_key(self.session_key))

    delete_if_exists = delete
