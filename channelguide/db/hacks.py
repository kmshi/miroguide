"""Hacks to SQLAlchemy."""

from sqlalchemy.databases import mysql
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
