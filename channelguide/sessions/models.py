from datetime import datetime, timedelta
import cPickle

from django.conf import settings
from sqlalchemy import mapper

from channelguide import db, cache
from channelguide.sessions import tables

class Session(object):
    def __init__(self):
        self.set_data({})

    def set_data(self, dict):
        self.data = cPickle.dumps(dict)

    def get_data(self):
        return cPickle.loads(self.data)

    def update_expire_date(self):
        age_timedelta = timedelta(seconds=settings.SESSION_COOKIE_AGE)
        self.expires = datetime.now() + age_timedelta

mapper(Session, tables.sessions)
cache.dont_clear_cache_for(Session)
