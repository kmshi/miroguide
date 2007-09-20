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

def connect():
    return pool.connect()

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
