import unittest
from sqlhelper import pool, testsetup

class DBPoolTest(unittest.TestCase):
    def setUp(self):
        self.max_connections = 3
        self.pool = pool.ConnectionPool(testsetup.dbinfo,
                self.max_connections, timeout=0)
        self.opened_connections = []

    def tearDown(self):
        for connection in self.opened_connections:
            try:
                connection.close()
            except:
                pass

    def connect(self):
        connection = self.pool.connect()
        self.opened_connections.append(connection)
        return connection
    
    def check_counts(self, used_count, free_count):
        self.assertEquals(self.pool.used_count, used_count)
        self.assertEquals(self.pool.free_count, free_count)

    def test_get_connection(self):
        for x in range(self.max_connections):
            self.connect()
        self.check_counts(self.max_connections, 0)
        self.assertRaises(pool.ConnectionTimeout, self.pool.connect)

    def test_release_connection(self):
        for x in range(self.max_connections):
            connection = self.connect()
        connection.close()
        self.check_counts(self.max_connections-1, 1)
        connection2 = self.connect()
        self.assert_(connection.raw_connection is connection2.raw_connection)
        self.check_counts(self.max_connections, 0)

    def test_close_connection(self):
        for x in range(self.max_connections):
            connection = self.connect()
        connection.destroy()
        self.check_counts(self.max_connections-1, 0)
        connection2 = self.connect()
        self.assert_(connection.raw_connection is not
                connection2.raw_connection)
        self.check_counts(self.max_connections, 0)

    def test_double_release(self):
        connection = self.connect()
        connection.close()
        self.assertRaises(ValueError, connection.close)
        self.assertRaises(ValueError, connection.destroy)
        self.check_counts(0, 1)

    def test_connection_closed_by_db(self):
        connection = self.connect()
        connection.close()
        # simulate the DB closing the connection while it's in the free pool
        connection.raw_connection.close()
        connection2 = self.pool.connect()
        self.assert_(connection is not connection2)
        self.assert_(connection2.is_open())

    def test_late_close(self):
        connection = self.connect()
        connection.close()
        connection2 = self.connect()
        self.assert_(connection.raw_connection is connection2.raw_connection)
        self.assertRaises(ValueError, connection.close)
