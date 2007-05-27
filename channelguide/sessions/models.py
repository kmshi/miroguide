from datetime import datetime, timedelta
import cPickle

from django.conf import settings
from sqlhelper.orm import Table, columns, Record

from channelguide import cache

# session changes only affect that one user's session, and we already handle
# sending different pages to logged in users.
cache.dont_clear_cache_for('cg_session')

session_table = Table('cg_session', 
        columns.String('session_key', 40, primary_key=True),
        columns.String('data'),
        columns.DateTime('expires'))

class Session(Record):
    table = session_table

    def __init__(self):
        Record.__init__(self)
        self.set_data({})
        self.session_key = None

    def set_data(self, dict):
        self.data = cPickle.dumps(dict)

    def get_data(self):
        return cPickle.loads(self.data)

    def update_expire_date(self):
        age_timedelta = timedelta(seconds=settings.SESSION_COOKIE_AGE)
        self.expires = datetime.now() + age_timedelta
