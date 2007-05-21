"""Connection pooling."""

import Queue
from threading import Condition, Lock

class ConnectionTimeout(Exception):
    """Timeout while waiting for a connection to be released to the pool."""

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
            if not self.dbinfo.is_connection_open(connection):
                # Connection was closed while it was in the free pool, open a
                # new one.
                connection = self.dbinfo.connect()
            self.used.add(connection)
            return connection
        finally:
            self.condition.release()

    def _get_connection(self):
        if self.free:
            return self.free.pop()
        elif len(self.used) + len(self.free) < self.max_connections:
            return self.dbinfo.connect()
        else:
            return None

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

    def close(self, connection):
        self.condition.acquire()
        try:
            self._remove_from_used(connection)
            self.condition.notify()
        finally:
            self.condition.release()
