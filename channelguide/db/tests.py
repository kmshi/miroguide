import os

from channelguide import db
from channelguide.testframework import TestCase
from channelguide.util import hash_string
import version
import middleware
import update

class DBUpdateTest(TestCase):
    def tearDown(self):
        self.connection.rollback()
        for table in ('robot', 'sitcom'):
            try:
                self.connection.execute("DROP TABLE %s" % table)
            except:
                pass
            else:
                self.connection.commit()
        TestCase.tearDown(self)

    def reset_version(self):
        self.connection.execute("DROP TABLE cg_db_version")
        version.initialize_version_table(self.connection)

    def test_versioning(self):
        self.reset_version()
        self.assertEquals(version.get_version(self.connection), -1)
        version.set_version(self.connection, 100)
        self.assertEquals(version.get_version(self.connection), 100)

    def check_columns(self, table_name, *correct_columns):
        results = self.connection.execute("DESCRIBE %s" % table_name)
        columns = [row[0] for row in results]
        self.assertSameSet(columns, correct_columns)

    def update_dir_path(self, dir):
        db_package_dir = os.path.dirname(__file__)
        return os.path.join(db_package_dir, "test_update_dirs", dir)

    def test_updates(self):
        self.reset_version()
        update.run_updates(self.connection, self.update_dir_path('robot'))
        self.assertEquals(version.get_version(self.connection), 3)
        self.check_columns('robot', 'serial', 'name', 'model_name',
                'laser_beams')
        rows = self.connection.execute("SELECT * from robot")
        self.assertEquals(len(rows), 1)
        self.assertEquals(rows[0], ("123abcdef", 'roy',
            hash_string("BOOyA-5000"), 2))

    def test_version_commit(self):
        self.reset_version()
        update.run_updates(self.connection, self.update_dir_path('robot'))
        new_connection = db.connect()
        self.assertEquals(version.get_version(new_connection), 3)
        new_connection.close()

    def test_run_updates_twice(self):
        self.reset_version()
        update.run_updates(self.connection, 'test_update_dirs/robot/')
        update.run_updates(self.connection, 'test_update_dirs/robot/')

    def test_migration_from_middle(self):
        self.reset_version()
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
        self.reset_version()
        self.assertRaises(Exception, update.run_updates, self.connection,
                self.update_dir_path('bad_foreign_key'))

class InnoDBTest(TestCase):
    """Make sure that all our tables are InnoDB"""

    def test_all_tables_are_innodb(self):
        myisam_tables = ['cg_channel_search_data', 'cg_item_search_data']
        results = self.connection.execute("SHOW TABLES")
        table_names = [row[0] for row in results]
        for table_name in table_names:
            if (table_name in myisam_tables or
                    table_name.startswith('django_')):
                continue
            rows = self.connection.execute("SHOW CREATE TABLE %s" % table_name)
            create_text = rows[0][1]
            if 'ENGINE=InnoDB' not in create_text:
                raise AssertionError("%s is not an InnoDB table" % table_name)

class MiddlewareTest(TestCase):
    def setUp(self):
        TestCase.setUp(self)
        self.middleware = middleware.DBMiddleware()

    def test_objects_are_added(self):
        request = self.process_request()
        self.assert_(hasattr(request, 'connection'))

    def test_transaction(self):
        version = self.connection.execute('SELECT version FROM cg_db_version')
        request = self.process_request()
        request.connection.execute(
                'INSERT INTO cg_db_version(version) VALUES(-123123)')
        exception = ValueError("OOPS")
        self.process_exception(request, exception)
        self.process_response(request)
        connection2 = db.connect()
        try:
            rows = connection2.execute("SELECT version FROM cg_db_version")
            self.assertEquals(list(rows), list(version))
        finally:
            connection2.close()
