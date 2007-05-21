class Connection(object):
    """Connection object.  This simplfies the python DB API's
    connection/cursor objects.  It has the following differences:

      * It stores both a connection and a cursor to that connection, so you
        can call execute(), commit() and rollback() on it.
      * execute() returns all the results immediately, no need for fetchall()
    """
    def __init__(self, raw_connection):
        self.raw_connection = raw_connection
        self.cursor = raw_connection.cursor()

    def execute(self, sql, args=None):
        self.cursor.execute(sql, args)
        return self.cursor.fetchall()

    def commit(self):
        self.raw_connection.commit()

    def rollback(self):
        self.raw_connection.rollback()

    def close(self):
        self.cursor.close()
        self.raw_connection.close()

    def get_lastrowid(self):
        return self.cursor.lastrowid
    lastrowid = property(get_lastrowid)
