from sqlhelper import orm, NotFoundError
from base import TestCase, Foo, Bar, Category, CategoryMap, Types, FooExtra
from datetime import datetime, timedelta

class UpdateTest(TestCase):
    def test_insert(self):
        f = Foo()
        f.id = 100
        f.name = 'cool'
        f.save(self.connection)
        f2 = Foo.get(self.connection, 100)
        self.assertEquals(f2.name, 'cool')

    def test_update(self):
        f = Foo.get(self.connection, 3)
        f.name = 'newname'
        f.save(self.connection)
        f2 = Foo.get(self.connection, 3)
        self.assertEquals(f2.name, 'newname')

    def test_double_save(self):
        f = Foo()
        f.id = 100
        f.name = 'cool'
        f.save(self.connection)
        f.name = 'cheesewhiz'
        f.save(self.connection)
        f2 = Foo.get(self.connection, 100)
        self.assertEquals(f2.name, 'cheesewhiz')

    def test_auto_increment(self):
        f = Foo()
        f.name = 'cool'
        f.save(self.connection)
        self.assert_(hasattr(f, 'id'))
        f2 = Foo.get(self.connection, f.id)
        self.assertEquals(f2.name, f.name)

    def test_change_primary_key(self):
        f = Foo()
        f.id = 1000
        f.name = 'newname'
        f.save(self.connection)
        self.assertEquals(f.rowid, (1000,))
        f.id = 2000
        f.save(self.connection)
        self.assertEquals(f.rowid, (2000,))
        f2 = Foo.get(self.connection, 2000)
        self.assertEquals(f2.name, f.name)
        self.assertRaises(NotFoundError, Foo.get, self.connection, 1000)

    def test_delete(self):
        for type in Types.query().execute(self.connection):
            type.delete(self.connection)
        results = Types.query().execute(self.connection)
        self.assertEquals(len(results), 0)

    def test_delete_then_save(self):
        foo = Foo()
        foo.id = 100
        foo.name = 'bingo'
        foo.save(self.connection)
        foo.delete(self.connection)
        self.assert_(not foo.exists_in_db())
        foo.save(self.connection)
        f2 = Foo.get(self.connection, 100)
        self.assertEquals(f2.name, 'bingo')

class AutoAssignmentTest(TestCase):
    def test_default(self):
        type = Types()
        type.boolean = True
        type.save(self.connection)
        self.assertEquals(type.string, "booya")
        self.assert_(datetime.now() - type.date < timedelta(seconds=1))
        self.assertEquals(type.null_ok, None)
        type2 = Types.get(self.connection, type.id)
        self.assertEquals(type.string, type2.string)
        # we should compare dates, but MySQL drops the microseconds, so
        # there's no point
        self.assertEquals(type.null_ok, type2.null_ok)

    def test_onupdate(self):
        type = Types()
        type.boolean = True
        type.save(self.connection)
        first_date = type.date
        type.save(self.connection)
        self.assert_(type.date > first_date)

    def test_set_foreign_keys(self):
        foo = Foo()
        foo.name = '123123'
        foo.save(self.connection)
        bar = Bar()
        bar.name = 'something'
        bar.parent = foo
        bar.save(self.connection)
        self.assertEquals(bar.foo_id, foo.id)
        foo_extra = FooExtra()
        foo_extra.extra_info = 'abcdef'
        foo_extra.foo = foo
        foo_extra.save(self.connection)
        self.assertEquals(foo_extra.id, foo.id)

    def test_dont_overwrite_foreign_keys(self):
        foo = Foo()
        foo.name = '123123'
        foo.save(self.connection)
        bar = Bar()
        bar.name = 'something'
        bar.foo_id = 3
        bar.foo = foo
        bar.save(self.connection)
        self.assertEquals(bar.foo_id, 3)


class ConvertForDBTest(TestCase):
    def test_string_conversion(self):
        self.pause_logging()
        f = Foo()
        f.name = 'a' * 40 # 40 chars isn't a problem
        f.save(self.connection)
        self.check_logging(warnings=0)
        f.name = 'a' * 50 # 50 is
        f.save(self.connection)
        self.check_logging(warnings=1)
        self.assertEquals(f.name, 'a' * 40)

    def test_string_conversion_null(self):
        type = Types()
        type.boolean = True
        type.null_ok = None
        type.save(self.connection)

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
        self.children.add_record(self.connection, self.make_new_child())
        self.assertEquals(len(self.children), self.initial_length+1)
        self.check_children_against_db()

    def test_remove(self):
        self.children.remove_record(self.connection, self.children[0])
        self.assertEquals(len(self.children), self.initial_length-1)
        self.check_children_against_db()

    def test_clear(self):
        self.children.clear(self.connection)
        self.assertEquals(len(self.children), 0)
        self.check_children_against_db()

    def test_add_many(self):
        new_children = [self.make_new_child() for i in range(5)]
        self.children.add_records(self.connection, new_children)
        self.assertEquals(len(self.children), self.initial_length+5)
        self.check_children_against_db()

class OneToManyListTest(_RelationListTest):
    def select_list(self):
        return Foo.get(self.connection, 3, join='bars').bars

    def make_new_child(self):
        child = Bar()
        child.name = 'test'
        return child

    def test_set_reflection(self):
        foo = Foo.get(self.connection, 3, join='bars')
        bar = self.make_new_child()
        foo.bars.add_record(self.connection, bar)
        self.assert_(bar.parent is foo)

class ManyToManyListTest(_RelationListTest):
    def select_list(self):
        return Foo.get(self.connection, 2, join='categories').categories

    def make_new_child(self):
        child = Category()
        child.name = 'test'
        child.save(self.connection)
        return child

