from sqlhelper import orm
from base import TestCase, Foo, Bar, Category, CategoryMap, Types
from datetime import datetime, timedelta

class UpdateTest(TestCase):
    def test_insert(self):
        f = Foo()
        f.id = 100
        f.name = 'cool'
        f.save(self.cursor)
        f2 = Foo.get(self.cursor, 100)
        self.assertEquals(f2.name, 'cool')

    def test_update(self):
        f = Foo.get(self.cursor, 3)
        f.name = 'newname'
        f.save(self.cursor)
        f2 = Foo.get(self.cursor, 3)
        self.assertEquals(f2.name, 'newname')

    def test_double_save(self):
        f = Foo()
        f.id = 100
        f.name = 'cool'
        f.save(self.cursor)
        f.name = 'cheesewhiz'
        f.save(self.cursor)
        f2 = Foo.get(self.cursor, 100)
        self.assertEquals(f2.name, 'cheesewhiz')

    def test_auto_increment(self):
        f = Foo()
        f.name = 'cool'
        f.save(self.cursor)
        self.assert_(hasattr(f, 'id'))
        f2 = Foo.get(self.cursor, f.id)
        self.assertEquals(f2.name, f.name)

    def test_change_primary_key(self):
        f = Foo()
        f.id = 1000
        f.name = 'newname'
        f.save(self.cursor)
        self.assertEquals(f.rowid, (1000,))
        f.id = 2000
        f.save(self.cursor)
        self.assertEquals(f.rowid, (2000,))
        f2 = Foo.get(self.cursor, 2000)
        self.assertEquals(f2.name, f.name)
        self.assertRaises(orm.NotFoundError, Foo.get, self.cursor, 1000)

    def test_delete(self):
        for type in Types.query().execute(self.cursor):
            type.delete(self.cursor)
        results = Types.query().execute(self.cursor)
        self.assertEquals(len(results), 0)

class AutoAssignmentTest(TestCase):
    def test_default(self):
        type = Types()
        type.boolean = True
        type.save(self.cursor)
        self.assertEquals(type.string, "booya")
        self.assert_(datetime.now() - type.date < timedelta(seconds=1))
        self.assertEquals(type.null_ok, None)
        type2 = Types.get(self.cursor, type.id)
        self.assertEquals(type.string, type2.string)
        # we should compare dates, but MySQL drops the microseconds, so
        # there's no point
        self.assertEquals(type.null_ok, type2.null_ok)

    def test_onupdate(self):
        type = Types()
        type.boolean = True
        type.save(self.cursor)
        first_date = type.date
        type.save(self.cursor)
        self.assert_(type.date > first_date)

class ConvertForDBTest(TestCase):
    def test_string_conversion(self):
        self.pause_logging()
        f = Foo()
        f.name = 'a' * 40 # 40 chars isn't a problem
        f.save(self.cursor)
        self.check_logging(warnings=0)
        f.name = 'a' * 50 # 50 is
        f.save(self.cursor)
        self.check_logging(warnings=1)
        self.assertEquals(f.name, 'a' * 40)

    def test_string_conversion_null(self):
        type = Types()
        type.boolean = True
        type.null_ok = None
        type.save(self.cursor)

class _RelationListTest(TestCase):
    # NOTE by prefixing the class name with _, it doesn't get exported.  This
    # is good, we don't want to run these tests, only the tests of our
    # subclasses.

    def setUp(self):
        TestCase.setUp(self)
        self.children = self.select_list()
        self.initial_length = len(self.children)

    def check_children_against_db(self):
        ids = [record.id for record in self.children]
        ids2 = [record.id for record in self.select_list()]
        self.assertSameSet(ids, ids2)

    def test_add(self):
        self.children.add_record(self.cursor, self.make_new_child())
        self.assertEquals(len(self.children), self.initial_length+1)
        self.check_children_against_db()

    def test_remove(self):
        self.children.remove_record(self.cursor, self.children[0])
        self.assertEquals(len(self.children), self.initial_length-1)
        self.check_children_against_db()

    def test_clear(self):
        self.children.clear(self.cursor)
        self.assertEquals(len(self.children), 0)
        self.check_children_against_db()

    def test_add_many(self):
        new_children = [self.make_new_child() for i in range(5)]
        self.children.add_records(self.cursor, new_children)
        self.assertEquals(len(self.children), self.initial_length+5)
        self.check_children_against_db()

class OneToManyListTest(_RelationListTest):
    def select_list(self):
        return Foo.get(self.cursor, 3, join='bars').bars

    def make_new_child(self):
        child = Bar()
        child.name = 'test'
        return child

class ManyToManyListTest(_RelationListTest):
    def select_list(self):
        return Foo.get(self.cursor, 2, join='categories').categories

    def make_new_child(self):
        child = Category()
        child.name = 'test'
        child.save(self.cursor)
        return child

