"""DBInfo classes.  The handle database-specific operations.

Right now there's only MySQL support, but it's trivial to add new databases.
"""

# NOTE: Don't import DB modules here, only import them in if the DBInfo class
# for that module is actually created (See MySQLDBInfo for how).

class DBInfoBase(object):
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


class MySQLDBInfo(DBInfoBase):
    def __init__(self, db, host, user, passwd, port=None):
        self.connect_args = { 
                'host': host,
                'db': db,
                'user': user,
                'passwd': passwd
        }
        if port is not None:
            self.connect_args['port'] = port

        self.module = __import__('MySQLdb')

    def connect(self):
        return self.module.connect(**self.connect_args)

    def connect_without_database(self):
        args = self.connect_args.copy()
        del args['db']
        return self.module.connect(**args)

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
