"""db

Database functions for channelguide.
"""

# import hacks as soon as possible, since it makes changes to sqlalchemy
import hacks

import os
import re

from sqlalchemy import (create_engine, create_session, BoundMetaData,
        object_session, class_mapper)
from sqlalchemy.engine.url import URL
from sqlalchemy.pool import QueuePool
from sqlalchemy.orm.mapper import global_extensions
from django.conf import settings
# NOTE: this next imports configures sqlalchemy to use the SelectResults 
# extension for all Mapper queries.  See:
# http://www.sqlalchemy.org/docs/plugins.myt#plugins_selectresults
import sqlalchemy.mods.selectresults
# Add our mapper extension that clears the cache when any object changes.
from channelguide import cache
global_extensions.append(cache.CacheClearMapperExtension)

from channelguide import util
import version
import update

engine_url = '%s://%s' % (settings.DATABASE_ENGINE, settings.DATABASE_USER)
if settings.DATABASE_PASSWORD:
    engine_url += ':%s' % settings.DATABASE_PASSWORD
engine_url += '@%s' % settings.DATABASE_HOST
if settings.DATABASE_PORT:
    engine_url += ':%s' % settings.DATABASE_PORT
engine_url += '/%s' % settings.DATABASE_NAME

engine = create_engine(engine_url, poolclass=QueuePool,
        max_overflow=5, pool_size=settings.MAX_DB_CONNECTIONS-5)
pool = engine.connection_provider._pool
metadata = BoundMetaData(engine)

def connect():
    return engine.connect()

def make_session():
    return create_session(bind_to=connect())

def syncdb(bind_to=None):
    if bind_to is None:
        bind_to = engine
    connection = bind_to.connect()
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

class DBObject(object):
    def session(self):
        return object_session(self)

    @classmethod
    def mapper(cls):
        return class_mapper(cls)

    def connection(self):
        return self.session().connection(self.mapper())
