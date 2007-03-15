"""Hacks to SQLAlchemy."""

from sqlalchemy.databases import mysql
from sqlalchemy.orm.mapper import global_extensions
from sqlalchemy import MapperExtension, EXT_PASS
from sqlalchemy.orm.properties import SynonymProperty
from sqlalchemy.orm.strategies import EagerLazyOption
import MySQLdb

class CGMySQLDialect(mysql.MySQLDialect):
    def do_execute_many(self, cursor, statement, parameters, **kwargs):
        try:
            cursor.executemany(statement, parameters)
        except MySQLdb.OperationalError, o:
            # (see do_execute)
            if o.args[0] == 2006 or o.args[0] == 2014:
                cursor.invalidate()
            raise o

    def do_execute(self, cursor, statement, parameters, **kwargs):
        try:
            cursor.execute(statement, parameters)
        except MySQLdb.OperationalError, o:
            # sqlalchemy only raises the exception when the if statement is
            # true, this seems like bad policy in general and one case I know
            # it breaks is bad foreign keys for InnoDB tables
            if o.args[0] == 2006 or o.args[0] == 2014:
                cursor.invalidate()
            raise o
mysql.dialect = CGMySQLDialect

class SynonymEagerLoadFixer(MapperExtension):
    """If the synonym feature of SQLAlchemies mapper doesn't seem to work with
    eagerload.  The class fixes that.
    """

    def _fix_options(self, query):
        fixed_options = []
        for option in query.with_options:
            if type(option) is EagerLazyOption:
                key_components = option.key.split(".")
                prop = query.mapper.props[key_components[0]]
                if type(prop) is SynonymProperty:
                    option = EagerLazyOption(prop.name, prop.proxy)
            fixed_options.append(option)
        query.with_options = fixed_options

    def select(self, query, arg=None, **kwargs):
        self._fix_options(query)
        return EXT_PASS

    def select_by(self, query, *args, **kwargs):
        self._fix_options(query)
        return EXT_PASS

global_extensions.append(SynonymEagerLoadFixer)
