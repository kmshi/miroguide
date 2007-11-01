# sqlhelper -- SQL helper tools
# Copyright (C) 2005-2007 Participatory Culture Foundation
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301 USA

"""DBInfo classes.  The handle database-specific operations.

Right now there's only MySQL and Postgres support, but it's trivial to add new
databases.
"""

# NOTE: Don't import DB modules here, only import them in if the DBInfo class
# for that module is actually created (See the examples below)

class DBInfoBase(object):
    engine = '' # fill in with a string identifier for your database engine

    def connect(self):
        raise NotImplementedError()

    def get_table_names(self, cursor):
        raise NotImplementedError()

    def is_connection_open(self, connection):
        raise NotImplementedError()

    def create_database(self):
        raise NotImplementedError()

    def drop_database(self):
        raise NotImplementedError()

    def get_autoincrement_value(self, cursor, table, column):
        raise NotImplementedError()

class MySQLDBInfo(DBInfoBase):
    """MySQL support requires the MySQLdb module.  """

    engine = 'mysql'

    def __init__(self, db, host, user, passwd, port=None, use_unicode=False):
        self.connect_args = { 
                'host': host,
                'db': db,
                'user': user,
                'passwd': passwd
        }
        if port is not None:
            self.connect_args['port'] = port
        if use_unicode:
            self.connect_args['use_unicode'] = True

    def connect(self):
        import MySQLdb
        return MySQLdb.connect(**self.connect_args)

    def connect_without_database(self):
        import MySQLdb
        args = self.connect_args.copy()
        del args['db']
        return MySQLdb.connect(**args)

    def create_database(self):
        """Create a new database to use for testing, then return a cursor to
        that database.
        """
        connection = self.connect_without_database()
        cursor = connection.cursor()
        cursor.execute("CREATE DATABASE %s" % self.connect_args['db'])
        connection.close()

    def drop_database(self):
        connection = self.connect_without_database()
        cursor = connection.cursor()
        cursor.execute("DROP DATABASE %s" % self.connect_args['db'])
        connection.close()

    def is_connection_open(self, connection):
        return connection.open

    def get_table_names(self, cursor):
        cursor.execute("SHOW TABLES")
        return [row[0] for row in cursor.fetchall()]

    def get_autoincrement_value(self, cursor, table, column):
        return cursor.lastrowid

class PostgreSQLDBInfo(DBInfoBase):
    """PostgreSQL support.  Requires psycopg2."""

    engine = 'postgresql'

    def __init__(self, db, host, user, passwd, port=None):
        self.dbname = db
        self.DSN = ("host='%s' dbname='%s' user='%s' password='%s'" %
                (host, db, user, passwd))
        self.NO_DB_DSN = ("host='%s' dbname='template1' user='%s' password='%s'" %
                (host, user, passwd))
        if port is not None:
            self.DSN += ' port=%s' % port
            self.NO_DB_DSN += ' port=%s' % port


    def connect(self):
        import psycopg2
        return psycopg2.connect(self.DSN)

    def connect_without_database(self):
        import psycopg2
        return psycopg2.connect(self.NO_DB_DSN)

    def execute_with_autocommit(self, connection, statement):
        import psycopg2.extensions
        old_isolation_level = connection.isolation_level
        connection.set_isolation_level(
                psycopg2.extensions.ISOLATION_LEVEL_AUTOCOMMIT)
        try:
            cursor = connection.cursor()
            cursor.execute(statement)
        finally:
            connection.set_isolation_level(old_isolation_level)

    def create_database(self):
        """Create a new database to use for testing, then return a cursor to
        that database.
        """
        connection = self.connect_without_database()
        try:
            self.execute_with_autocommit(connection,
                    "CREATE DATABASE %s" % self.dbname)
        finally:
            connection.close()

    def drop_database(self):
        connection = self.connect_without_database()
        try:
            self.execute_with_autocommit(connection,
                    "DROP DATABASE %s" % self.dbname)
        finally:
            connection.close()

    def is_connection_open(self, connection):
        return not connection.closed

    def get_table_names(self, cursor):
        cursor.execute("SELECT tablename FROM pg_tables "
                 "WHERE tablename NOT LIKE 'pg_%' AND "
                 "tablename NOT LIKE 'sql_%'")
        return [row[0] for row in cursor.fetchall()]

    def get_autoincrement_value(self, cursor, table, column):
        cursor.execute("SELECT CURRVAL('\"%s_%s_seq\"')" % (table, column))
        return cursor.fetchone()[0]
