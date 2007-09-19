"""db

Database functions for channelguide.
"""

import os
import re

from sqlhelper.pool import ConnectionPool
from sqlhelper.dbinfo import MySQLDBInfo
from channelguide.cache import client
from channelguide import util
import version
import update

from django.conf import settings

kwargs = { 
        'host': settings.DATABASE_HOST,
        'db': settings.DATABASE_NAME,
        'user': settings.DATABASE_USER, 
        'passwd': settings.DATABASE_PASSWORD
}
if settings.DATABASE_PORT:
    kwargs['port'] = settings.DATABASE_PORT
dbinfo = MySQLDBInfo(**kwargs)
pool = ConnectionPool(dbinfo, settings.MAX_DB_CONNECTIONS)

class CachingConnectionWrapper(object):
    def __init__(self, connection):
        self.connection = connection

    def __getattr__(self, attr):
        if attr in self.__dict__:
            return self.__dict__[attr]
        else:
            return getattr(self.connection, attr)

    @staticmethod
    def get_key(sql, args):
        return 'SQL%s' % hash((sql, args))

    @staticmethod
    def can_cache(sql, args):
        return sql.upper().startswith('SELECT') and 'user' not in sql

    def execute(self, sql, args):
        if self.can_cache(sql, args):
            cached = client.get(self.get_key(sql, args))
            if cached:
                return cached
        ret = self.connection.execute(sql, args)
        if self.can_cache(sql, args):
            client.set(self.get_key(sql, args), ret, time=60)
        return ret


def connect():
    c = pool.connect()
    return CachingConnectionWrapper(c)

def syncdb():
    connection = connect()
    version.initialize_version_table(connection)
    update_dir = os.path.join(os.path.dirname(__file__), 'updates')
    update.run_updates(connection, update_dir)
    connection.close()

def execute_file(path):
    empty_re = re.compile(r'\s*$')
    comment_re = re.compile(r'\s*--')
    for statement in util.read_file(path).split(';'):
        if not (empty_re.match(statement) or comment_re.match(statement)):
            engine.execute(statement)
