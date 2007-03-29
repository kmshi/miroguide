from datetime import datetime, timedelta
import cPickle
import random

from django.conf import settings
from sqlalchemy import mapper

from channelguide import db, cache
from channelguide.sessions import tables
from channelguide.util import hash_string

class Session(object):
    def __init__(self, db_session):
        self.session_key = self.make_new_session_key(db_session)
        self.set_data({})

    @staticmethod
    def make_new_session_key(db_session):
        # This should be fairly secure as long as the random seed is not
        # possible to guess by an attacker.
        while 1:
            randstring = '%x' % random.getrandbits(128)
            key = hash_string(randstring + settings.SECRET_KEY)
            if db_session.get(Session, key) is None:
                return key

    def set_data(self, dict):
        self.data = cPickle.dumps(dict)

    def get_data(self):
        return cPickle.loads(self.data)

    def update_expire_date(self):
        age_timedelta = timedelta(seconds=settings.SESSION_COOKIE_AGE)
        self.expires = datetime.now() + age_timedelta

    @staticmethod
    def get_from_key(db_session, session_key):
        """Gets a session object using a session_key.  If session_key is
        None, doesn't exist in the DB or the session associated with it has
        expired a new Session will be created.
        """

        if session_key is None:
            return Session(db_session)
        session = db_session.get(Session, session_key)
        if session is None:
            return Session(db_session)
        if session.expires < datetime.now():
            db_session.delete(session)
            return Session(db_session)
        return session

mapper(Session, tables.sessions)
cache.dont_clear_cache_for(Session)
