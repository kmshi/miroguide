import os

from sqlalchemy import BoundMetaData, Table, mapper

from channelguide.testframework import TestCase, drop_tables
from channelguide.db import connect, engine, syncdb
from channelguide.util import hash_string
import version
import middleware
import update

class DBUpdateTest(TestCase):
    def setUp(self):
        TestCase.setUp(self)
        # we don't want anything in the database when we do these tests
        drop_tables()

    def tearDown(self):
        # restore the real database schema
        for table in ('robot', 'sitcom'):
            if self.connection.engine.has_table(table):
                self.connection.execute("DROP TABLE %s" % table)
        self.connection.execute("DROP TABLE cg_db_version")
        syncdb()
        TestCase.tearDown(self)

    def test_versioning(self):
        version.initialize_version_table(self.connection)
        self.assertEquals(version.get_version(self.connection), -1)
        version.set_version(self.connection, 100)
        self.assertEquals(version.get_version(self.connection), 100)

    def check_columns(self, table_name, *correct_columns):
        meta = BoundMetaData(self.connection.engine)
        table = Table(table_name, meta, autoload=True)
        self.assertSameSet([col.name for col in table.c], correct_columns)

    def update_dir_path(self, dir):
        db_package_dir = os.path.dirname(__file__)
        return os.path.join(db_package_dir, "test_update_dirs", dir)

    def test_updates(self):
        version.initialize_version_table(self.connection)
        update.run_updates(self.connection, self.update_dir_path('robot'))
        self.assertEquals(version.get_version(self.connection), 3)
        self.check_columns('robot', 'serial', 'name', 'model_name',
                'laser_beams')
        meta = BoundMetaData(self.connection.engine)
        robot = Table('robot', meta, autoload=True)
        robots = robot.select().execute().fetchall()
        self.assertEquals(len(robots), 1)
        self.assertEquals(robots[0], ("123abcdef", 'roy',
            hash_string("BOOyA-5000"), 2))

    def test_run_updates_twice(self):
        version.initialize_version_table(self.connection)
        update.run_updates(self.connection, 'test_update_dirs/robot/')
        update.run_updates(self.connection, 'test_update_dirs/robot/')

    def test_migration_from_middle(self):
        version.initialize_version_table(self.connection)
        self.connection.execute("""\
CREATE TABLE sitcom (
  title VARCHAR(100) NOT NULL PRIMARY KEY,
  plot_summary VARCHAR(100) NOT NULL,
  wacky_neighbor VARCHAR(100) NOT NULL,
  viewers INTEGER NOT NULL
);""")
        self.check_columns('sitcom', 'title', 'plot_summary',
                'wacky_neighbor', 'viewers')
        version.set_version(self.connection, 3)
        update.run_updates(self.connection, self.update_dir_path('sitcom'))
        self.check_columns('sitcom', 'title', 'plot_summary', 'wacky_neighbor',
                'viewer_count')

    def test_bad_update_script(self):
        version.initialize_version_table(self.connection)
        self.assertRaises(Exception, update.run_updates, self.connection,
                self.update_dir_path('bad_foreign_key'))

class InnoDBTest(TestCase):
    """Make sure that all our tables are InnoDB"""

    def test_all_tables_are_innodb(self):
        myisam_tables = ['cg_channel_search_data', 'cg_item_search_data']
        connection = connect()
        metadata = BoundMetaData(connection.engine)
        table_names = [row[0] for row in connection.execute("SHOW TABLES")]
        for table_name in table_names:
            if table_name in myisam_tables:
                continue
            table = Table(table_name, metadata, autoload=True)
            engine_type = table.kwargs['mysql_engine'].split(' ')[0]
            self.assertEquals(engine_type, "InnoDB")
        connection.close()

class MiddlewareTest(TestCase):
    def setUp(self):
        TestCase.setUp(self)
        self.middleware = middleware.DBMiddleware()

    def test_objects_are_added(self):
        request = self.process_request()
        self.assert_(hasattr(request, 'db_session'))
        self.assert_(hasattr(request, 'connection'))

    def test_session_is_flushed(self):
        request = self.process_request()
        metadata = BoundMetaData(engine)
        version_table = Table('cg_db_version', metadata, autoload=True)
        version_table.delete().execute()
        class DBVersion(object):
            def __init__(self, version):
                self.version = version
        mapper(DBVersion, version_table, primary_key=[version_table.c.version])
        version_obj = DBVersion(123)
        request.db_session.save(version_obj)
        self.process_response(request)
        self.assertEquals(version.get_version(engine), 123)

    def test_transaction(self):
        request = self.process_request()
        connection = request.transaction.connection(None)
        metadata = BoundMetaData(engine)
        version_table = Table('cg_db_version', metadata, autoload=True)
        connection.execute(version_table.insert(), version=123)
        exception = ValueError("OOPS")
        self.process_exception(request, exception)
        self.process_response(request)
        self.assertEquals(request.transaction, None)
        connection2 = connect()
        self.assertEquals(list(connection2.execute(version_table.select())), 
                [(self.starting_db_version,)])
