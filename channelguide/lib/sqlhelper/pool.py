"""Connection pooling."""

import Queue
from threading import Semaphore

class ConnectionTimeout(Exception):
    """Timeout while waiting for a connection to be released to the pool."""

class ConnectionPool(object):
    def __init__(self, connector, max_connections, timeout=5):
        """Created a ConnectionPool.  connector is a function that will return
        a new connection.
        """

        self.connector = connector
        self.timeout = timeout
        self.free = Queue.Queue()
        self.semaphore = Semaphore(max_connections)
        self.free_count = 0
        self.used_count = 0

    def connect(self):
        try:
            return self.get_free_connection(0)
        except Queue.Empty:
            pass
        if self.semaphore.acquire(blocking=False):
            self.used_count += 1
            return self.connector()
        else:
            try:
                return self.get_free_connection(self.timeout)
            except Queue.Empty:
                raise ConnectionTimeout()

    def get_free_connection(self, timeout):
        connection = self.free.get(timeout)
        self.free_count -= 1
        self.used_count += 1
        # maybe the DB closed the connection while it was sitting in the fre
        # pool, if so, open a new one.  We don't need to mess with the
        # semaphore count for this, since we're replacing a connection that
        # was supposed to be free, with a new connection.
        if not connection.open:
            return self.connector()
        return connection

    def release(self, connection):
        self.free.put(connection)
        self.used_count -= 1
        self.free_count += 1

    def close(self, connection):
        self.semaphore.release()
        connection.close()
        self.used_count -= 1
