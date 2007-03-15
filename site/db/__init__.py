"""db

Database functions for channelguide.
"""

# import hacks as soon as possible, since it makes changes to sqlalchemy
import hacks

import os
import re

from sqlalchemy import create_engine, create_session, BoundMetaData
from sqlalchemy.engine.url import URL
from django.conf import settings
# NOTE: this next imports configures sqlalchemy to use the SelectResults 
# extension for all Mapper queries.  See:
# http://www.sqlalchemy.org/docs/plugins.myt#plugins_selectresults
import sqlalchemy.mods.selectresults

from channelguide.util import read_file
import version
import update

engine_url = '%s://%s' % (settings.DATABASE_ENGINE, settings.DATABASE_USER)
if settings.DATABASE_PASSWORD:
    engine_url += ':%s' % settings.DATABASE_PASSWORD
engine_url += '@%s' % settings.DATABASE_HOST
if settings.DATABASE_PORT:
    engine_url += ':%s' % settings.DATABASE_PORT
engine_url += '/%s' % settings.DATABASE_NAME

engine = create_engine(engine_url)
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
    for statement in read_file(path).split(';'):
        if not (empty_re.match(statement) or comment_re.match(statement)):
            engine.execute(statement)

def add_aggregate_column(function, from_obj, *filters):
    """Add a column that is a scalar subquery column to a select statement.

    Arguments:

    function -- aggregate function to use
    from_obj -- from_obj to perform the subquery on.  
    """
    subquery = select([function], from_obj=from_obj, scalar=True)
    for filter in filters:
        select.append_whereclause(filter)
    return select

    if defaultwhereclause:
        for col in table.col:
            for fk in col.foreign_keys:
                if fk.references(primary):
                    crit.append(primary.corresponding_column(fk.column) == fk.parent)
                    constraints.add(fk.constraint)
                    self.foreignkey = fk.parent

    pass

def count_column(table, whereclauseextra=None):
    pass
