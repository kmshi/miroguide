"""Connection pooling."""

import Queue
from threading import Condition, Lock

from sqlhelper import connection

class ConnectionTimeout(Exception):
    """Timeout while waiting for a connection to be released to the pool."""

class PooledConnection(connection.Connection):
    def __init__(self, raw_connection, pool):
        super(PooledConnection, self).__init__(raw_connection ,
            logging='/tmp/sql.log')
        self.pool = pool

    def clone(self):
        return PooledConnection(self.raw_connection, self.pool)

    def close(self):
        self.pool.release(self)

    def close_raw_connection(self):
        self.cursor.close()
        self.raw_connection.close()

    def destroy(self):
        self.close_raw_connection()
        self.pool.remove(self)

class ConnectionPool(object):
    def __init__(self, dbinfo, max_connections, timeout=5):
        self.dbinfo = dbinfo
        self.timeout = timeout
        self.max_connections = max_connections
        self.free = []
        self.used = set()
        self.lock = Lock()
        self.condition = Condition(self.lock)

    def get_free_count(self):
        self.lock.acquire()
        try:
            return len(self.free)
        finally:
            self.lock.release()

    def get_used_count(self):
        self.lock.acquire()
        try:
            return len(self.used)
        finally:
            self.lock.release()

    free_count = property(get_free_count)
    used_count = property(get_used_count)

    def connect(self):
        self.condition.acquire()
        try:
            connection = self._get_connection()
            if connection is None:
                self.condition.wait(self.timeout)
                connection = self._get_connection()
                if connection is None:
                    raise ConnectionTimeout()
            if not self.dbinfo.is_connection_open(connection.raw_connection):
                # Connection was closed while it was in the free pool, open a
                # new one.
                connection = self.make_new_connection()
            self.used.add(connection)
            return connection
        finally:
            self.condition.release()

    def _get_connection(self):
        if self.free:
            return self.free.pop().clone()
        elif len(self.used) + len(self.free) < self.max_connections:
            return self.make_new_connection()
        else:
            return None

    def make_new_connection(self):
        return PooledConnection(self.dbinfo.connect(), self)

    def _remove_from_used(self, connection):
        try:
            self.used.remove(connection)
        except KeyError:
            raise ValueError("Connection not in pool")

    def release(self, connection):
        self.condition.acquire()
        try:
            self._remove_from_used(connection)
            self.free.append(connection)
            self.condition.notify()
        finally:
            self.condition.release()

    def remove(self, connection):
        self.condition.acquire()
        try:
            self._remove_from_used(connection)
            self.condition.notify()
        finally:
            self.condition.release()
