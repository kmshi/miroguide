import logging
from datetime import datetime
import unittest

from sqlhelper import connection, orm, testsetup
from sqlhelper.orm import columns

class LogRaiser(logging.Handler):
    """Turns any distrubing log messages into exceptions."""
    def emit(self, record):
        if record.levelno >= logging.WARN:
            raise ValueError("got %s log record during tests" %
                    record.levelname)
class LogCatcher(logging.Filter):
    """Filters out log messages before LogRaiser raises them.  Stores the log
    messages that got saved so that they can be checked by TestCases.
    """
    def __init__(self):
        logging.Filter.__init__(self)
        self.records_seen = []
    def filter(self, record):
        self.records_seen.append(record)
        return 0
    def get_level_counts(self):
        counts = {}
        for rec in self.records_seen:
            counts[rec.levelno] = counts.get(rec.levelno, 0) + 1
        return counts
    def reset(self):
        self.records_seen = []

class TestCase(unittest.TestCase):
    def setUp(self):
        unittest.TestCase.setUp(self)
        self.connection = connection.Connection(testsetup.dbinfo.connect())
        #self.drop_all_tables()
        self.log_handler = LogRaiser()
        self.log_filter = LogCatcher()
        logging.getLogger().addHandler(self.log_handler)
        self.create_test_tables()
        self.populate_test_tables()

    def tearDown(self):
        self.drop_test_tables()
        logging.getLogger().removeFilter(self.log_filter)
        logging.getLogger().removeHandler(self.log_handler)
        self.connection.close()
        unittest.TestCase.tearDown(self)

    def pause_logging(self):
        logging.getLogger().addFilter(self.log_filter)

    def check_logging(self, infos=0, warnings=0, errors=0):
        counts = self.log_filter.get_level_counts()
        self.assertEquals(infos, counts.get(logging.INFO, 0))
        self.assertEquals(warnings, counts.get(logging.WARN, 0))
        self.assertEquals(errors, counts.get(logging.ERROR, 0))

    def assertSameSet(self, iterable1, iterable2):
        self.assertEquals(set(iterable1), set(iterable2))
        self.assertEquals(len(iterable1), len(iterable2))

    def resume_logging(self):
        logging.getLogger().removeFilter(self.log_filter)
        self.log_filter.reset()

    def create_test_tables(self):
        self.connection.execute("""CREATE TABLE foo (
id INT(11) NOT NULL AUTO_INCREMENT,
name VARCHAR(40) NOT NULL,
PRIMARY KEY (id))
ENGINE=InnoDB DEFAULT CHARSET=utf8;""")
        self.connection.execute("""CREATE TABLE foo_extra (
id INT(11) NOT NULL,
extra_info VARCHAR(40) NOT NULL,
PRIMARY KEY (id),
FOREIGN KEY (id) REFERENCES foo (id) ON DELETE CASCADE)
ENGINE=InnoDB DEFAULT CHARSET=utf8;""")
        self.connection.execute("""CREATE TABLE types (
id INT(11) NOT NULL AUTO_INCREMENT,
string VARCHAR(40) NOT NULL,
date DATETIME NOT NULL,
boolean TINYINT(1) NOT NULL,
null_ok VARCHAR(20) NULL,
PRIMARY KEY (id))
ENGINE=InnoDB DEFAULT CHARSET=utf8;""")
        self.connection.execute("""CREATE TABLE bar (
id INT(11) NOT NULL AUTO_INCREMENT,
foo_id INT(11), 
name VARCHAR(40) NOT NULL,
PRIMARY KEY (id),
FOREIGN KEY (foo_id) REFERENCES foo (id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8;""")
        self.connection.execute("""CREATE TABLE category (
id INT(11) NOT NULL AUTO_INCREMENT,
name VARCHAR(40) NOT NULL,
PRIMARY KEY (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8;""")
        self.connection.execute("""CREATE TABLE category_map (
category_id INT(11),
foo_id INT(11),
FOREIGN KEY (category_id) REFERENCES category (id) ON DELETE CASCADE,
FOREIGN KEY (foo_id) REFERENCES foo (id) ON DELETE CASCADE,
PRIMARY KEY (category_id, foo_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8;""")
        self.connection.execute("""CREATE TABLE category_map_with_dups (
category_id INT(11),
foo_id INT(11),
other_column INT(11),
FOREIGN KEY (category_id) REFERENCES category (id) ON DELETE CASCADE,
FOREIGN KEY (foo_id) REFERENCES foo (id) ON DELETE CASCADE,
PRIMARY KEY (category_id, foo_id, other_column)
) ENGINE=InnoDB DEFAULT CHARSET=utf8;""")

    def drop_test_tables(self):
        self.connection.execute("DROP TABLE category_map_with_dups")
        self.connection.execute("DROP TABLE category_map")
        self.connection.execute("DROP TABLE category")
        self.connection.execute("DROP TABLE bar")
        self.connection.execute("DROP TABLE foo_extra")
        self.connection.execute("DROP TABLE foo")
        self.connection.execute("DROP TABLE types")

    def populate_test_tables(self):
        self.populate_foo()
        self.populate_foo_extra()
        self.populate_types()
        self.populate_bar()
        self.populate_categories()

    def populate_foo(self):
        self.foo_values = [ (1, 'booya'), (2, 'car'), (3, 'toy'), (4, 'moo'),
                (5, 'cow')
        ]
        for id, name in self.foo_values:
            self.connection.execute("INSERT INTO foo(id, name) VALUES (%s, %s)",
                    (id, name))

    def populate_foo_extra(self):
        self.foo_extra_values = { 3: 'bacon', 2: 'oj' }
        for id, extra in self.foo_extra_values.items():
            sql = "INSERT INTO foo_extra(id, extra_info) VALUES(%s, %s)"
            self.connection.execute(sql, (id, extra))

    def populate_types(self):
        self.connection.execute("INSERT INTO "
                "types(id, string, date, boolean, null_ok) "
                "VALUES (2, 'false', '2005-08-02 15:00:25', 0, NULL)")
        self.connection.execute("INSERT INTO "
                "types(id, string, date, boolean, null_ok) "
                "VALUES (1, 'true', '2005-08-02 15:00:25', 1, 'abc')")
        self.null_type_ids = [2]
        self.nonnull_type_ids = [1]

    def populate_bar(self):
        self.bar_values = [ (1, 1, 'cat'), (2, 1, 'dog'), (3, 2, 'tiger'),
                (4, 3, 'squirel')
        ]
        self.foo_to_bars = {}
        for id, foo_id, name in self.bar_values:
            self.connection.execute("INSERT INTO bar(id, foo_id, name) "
                    "VALUES (%s, %s, %s)", (id, foo_id, name))
            bars = self.foo_to_bars.setdefault(foo_id, [])
            bars.append((id, foo_id, name))

    def populate_categories(self):
        self.category_values = [ (1, 'funny'), (2, 'tech'), (3, 'politics') ]
        for id, name in self.category_values:
            self.connection.execute("INSERT INTO category(id, name) "
                    "VALUES (%s, %s)", (id, name))
        self.foo_to_categories = {
                1: [1,2],
                2: [1,2,3],
                4: [3],
        }
        self.category_to_foos = {}
        for foo_id, category_ids in self.foo_to_categories.items():
            for cat_id in category_ids:
                self.connection.execute("INSERT INTO category_map "
                "(foo_id, category_id) VALUES (%s, %s)", (foo_id, cat_id))
                self.connection.execute("INSERT INTO category_map_with_dups "
                        "(foo_id, category_id, other_column) "
                        "VALUES (%s, %s, 1)", (foo_id, cat_id))
                self.connection.execute("INSERT INTO category_map_with_dups "
                        "(foo_id, category_id, other_column) "
                        "VALUES (%s, %s, 2)", (foo_id, cat_id))
                self.connection.execute("INSERT INTO category_map_with_dups "
                        "(foo_id, category_id, other_column) "
                        "VALUES (%s, %s, 3)", (foo_id, cat_id))
                try:
                    self.category_to_foos[cat_id].append(foo_id)
                except KeyError:
                    self.category_to_foos[cat_id] = [foo_id]


foo_table = orm.Table('foo', 
        columns.Int('id', primary_key=True, auto_increment=True), 
        columns.String('name', 40),
        columns.Subquery('category_count', """\
SELECT COUNT(*) 
FROM category_map AS map 
WHERE map.foo_id=#table#.id"""),
        columns.Subquery('bar_count', """\
SELECT COUNT(*) FROM bar WHERE bar.foo_id=#table#.id"""))

foo_extra_table = orm.Table('foo_extra', 
        columns.Int('id', primary_key=True, fk=foo_table.c.id),
        columns.String('extra_info', 255))

bar_table = orm.Table('bar', 
        columns.Int('id', primary_key=True, auto_increment=True), 
        columns.Int('foo_id', fk=foo_table.c.id), 
        columns.String('name', 200))
category_table = orm.Table('category', 
        columns.Int('id', primary_key=True, auto_increment=True),
        columns.String('name', 200))
category_map_table = orm.Table('category_map',
        columns.Int('foo_id', fk=foo_table.c.id, primary_key=True),
        columns.Int('category_id', fk=category_table.c.id, primary_key=True),
    )
category_map_with_dups_table = orm.Table('category_map_with_dups',
        columns.Int('foo_id', fk=foo_table.c.id, primary_key=True),
        columns.Int('category_id', fk=category_table.c.id, primary_key=True),
        columns.Int('other_column', primary_key=True),
    )
types_table = orm.Table('types',
        columns.Int('id', primary_key=True, auto_increment=True), 
        columns.String('string', 200, default="booya"),
        columns.DateTime('date', default=datetime.now, onupdate=datetime.now),
        columns.Boolean('boolean'),
        columns.String('null_ok', 20))

foo_table.one_to_many('bars', bar_table, backref='parent')
foo_table.one_to_one('extra', foo_extra_table, backref='foo')
foo_table.many_to_many('categories', category_table, category_map_table,
        backref='foos')
foo_table.many_to_many('categories_with_dups', category_table,
        category_map_with_dups_table, backref='foos')
category_map_table.many_to_one('foo', foo_table, backref='category_maps')
category_map_table.many_to_one('category', category_table,
        backref='category_maps')

class Foo(orm.Record): 
    table = foo_table
    def __str__(self): return self.name
    @classmethod
    def query_with_category_count(cls):
        return cls.query().load('category_count')
    @classmethod
    def query_with_bar_count(cls):
        return cls.query().load('bar_count')
    @classmethod
    def query_with_counts(cls):
        # note this is purposely in a different order than they are defined in
        # the table, to check if that screws things up.
        return cls.query().load('bar_count', 'category_count')
class FooExtra(orm.Record): 
    table = foo_extra_table
class Bar(orm.Record): 
    table = bar_table
    def __str__(self): return self.name
class Category(orm.Record): 
    table = category_table
    def __str__(self): return self.name
class CategoryMap(orm.Record): 
    table = category_map_table
class Types(orm.Record):
    table = types_table
