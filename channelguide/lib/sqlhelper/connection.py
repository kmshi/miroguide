import time
class Connection(object):
    """Connection object.  This simplfies the python DB API's
    connection/cursor objects.  It has the following differences:

      * It stores both a connection and a cursor to that connection, so you
        can call execute(), commit() and rollback() on it.
      * execute() returns all the results immediately, no need for fetchall()
    """
    def __init__(self, raw_connection, logging=False):
        self.raw_connection = raw_connection
        self.cursor = raw_connection.cursor()
        if logging is not False:
            self.logfile = file(logging, 'a')
        else:
            self.logfile = None

    def execute(self, sql, args=None):
        s = time.time()
        self.cursor.execute(sql, args)
        t = time.time()
        rows = self.cursor.fetchall()
        v = time.time()
        if self.logfile is not None and not sql.startswith('SELECT'):
            self.logfile.write("""executing %r
with args: %r
execute took %f seconds
fetchall took %f seconds
""" % (sql, args, (t-s), (v-t)))
        return rows

    def commit(self):
        self.raw_connection.commit()

    def rollback(self):
        self.raw_connection.rollback()

    def close(self):
        self.cursor.close()
        self.raw_connection.close()
        if self.logfile is not None:
            self.logfile.close()

    def get_lastrowid(self):
        return self.cursor.lastrowid
    lastrowid = property(get_lastrowid)
