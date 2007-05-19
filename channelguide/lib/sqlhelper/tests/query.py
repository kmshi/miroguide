import datetime 

from sqlhelper import orm, NotFoundError, TooManyResultsError
from base import TestCase, Foo, Bar, Category, CategoryMap, Types, FooExtra

class QueryTest(TestCase):
    def checkFoos(self, foos, value_check):
        foo_values = [(foo.id, foo.name) for foo in foos]
        self.assertSameSet(foo_values, value_check)

    def check_bars(self, foo):
        bar_values = [(bar.id, bar.foo_id, bar.name) for bar in foo.bars]
        self.assertSameSet(bar_values, self.foo_to_bars.get(foo.id, []))

    def test_select(self):
        self.checkFoos(Foo.query().execute(self.cursor), self.foo_values)

    def test_types(self):
        for obj in Types.query().execute(self.cursor):
            self.assertEquals(type(obj.id), long)
            self.assertEquals(type(obj.string), str)
            self.assertEquals(type(obj.date), datetime.datetime)
            self.assertEquals(type(obj.boolean), bool)
            self.assertEquals(obj.null_ok, None)

    def test_boolean_convert(self):
        def get_by_name(name):
            s = Types.query().filter(Types.c.string==name)
            return s.execute(self.cursor)[0]
        false_type = get_by_name('false')
        true_type = get_by_name('true')
        self.assertEquals(false_type.boolean, False)
        self.assertEquals(true_type.boolean, True)

    def test_where(self):
        results = Foo.query().filter(id=3).execute(self.cursor)
        matching_values = [(id, name) for id, name in self.foo_values
                if id == 3]
        self.checkFoos(results, matching_values)
        results = Foo.query().filter(name='bacon').execute(self.cursor)
        matching_values = [(id, name) for id, name in self.foo_values
                if name == 'bacon']
        self.checkFoos(results, matching_values)

    def test_order_by(self):
        query = Foo.query().order_by(Foo.c.name)
        results = query.execute(self.cursor)
        for i in range(len(results) - 1):
            self.assert_(results[i].name <= results[i+1].name)
        query = Foo.query().order_by('name', desc=True)
        results = query.execute(self.cursor)
        for i in range(len(results) - 1):
            self.assert_(results[i].name >= results[i+1].name)

    def test_multiple_order_by(self):
        query = Foo.query_with_bar_count().order_by('bar_count', desc=True)
        query.order_by('name', desc=False)
        results = query.execute(self.cursor)
        for i in range(len(results) - 1):
            self.assert_(results[i].bar_count >= results[i+1].bar_count)
            if results[i].bar_count == results[i+1].bar_count:
                self.assert_(results[i].name <= results[i+1].name)

    def test_reset_order_by(self):
        query = Foo.query().order_by('id', desc=False)
        query.order_by(None)
        query.order_by('name')
        results = query.execute(self.cursor)
        for i in range(len(results) - 1):
            self.assert_(results[i].name <= results[i+1].name)

    def test_limit(self):
        results = Foo.query().limit(2).execute(self.cursor)
        self.assertEquals(len(results), 2)

    def test_offset(self):
        all_results = Foo.query().order_by(Foo.c.name).execute(self.cursor)
        some_results = Foo.query().order_by(Foo.c.name).offset(2).execute(self.cursor)
        for foo1, foo2 in zip(all_results[2:], some_results):
            self.assertEquals(foo1.id, foo2.id)

    def test_get(self):
        foo = Foo.get(self.cursor, 3)
        self.assertEquals(foo.id, 3)
        self.assertRaises(NotFoundError, Foo.get, self.cursor, 999999)
        query = Foo.query().filter(Foo.c.id > 2)
        self.assertRaises(TooManyResultsError, query.get, self.cursor)

    def test_count(self):
        s = Foo.query().filter((Foo.c.id == 4) | (Foo.c.id <= 2))
        self.assertEquals(s.count(self.cursor), 3)

    def test_one_to_many(self):
        foos = Foo.query().join('bars').execute(self.cursor)
        for foo in foos:
            self.check_bars(foo)
            for bar in foo.bars:
                self.assertEquals(bar.parent, foo)
        self.checkFoos(foos, self.foo_values)

    def check_bar_parent(self, bar):
        for id, foo_id, name in self.bar_values:
            if id == bar.id:
                self.assertEquals(foo_id, bar.parent.id)
                return
        raise AssertionError("bar not found")

    def test_many_to_one(self):
        for bar in Bar.query().join("parent").execute(self.cursor):
            self.check_bar_parent(bar)

    def check_categories(self, foo):
        self.assertSameSet( [c.id for c in foo.categories],
                    self.foo_to_categories.get(foo.id, []))

    def test_many_to_many(self):
        foos = Foo.query().join('categories').execute(self.cursor)
        for foo in foos:
            self.check_categories(foo)
        self.checkFoos(foos, self.foo_values)

        categories = Category.query().join("foos").execute(self.cursor)
        for cat in categories:
            self.assertSameSet([c.id for c in cat.foos],
                    self.category_to_foos.get(cat.id, []))

    def test_many_to_many_with_dups(self):
        foo_relations = Foo.table.relations
        self.assert_(not foo_relations['categories'].use_exists_subquery)
        self.assert_(foo_relations['categories_with_dups'].use_exists_subquery)
        query = Foo.query().join('categories_with_dups')
        rows_seen = set()
        for row in query.make_select().execute(self.cursor):
            if row in rows_seen:
                raise AssertionError("Duplicate row selected")
            rows_seen.add(row)
        for foo in query.execute(self.cursor):
            self.assertSameSet( [c.id for c in foo.categories_with_dups],
                    self.foo_to_categories.get(foo.id, []))

    def test_one_to_one(self):
        foos = Foo.query().join("extra").execute(self.cursor)
        self.checkFoos(foos, self.foo_values)
        for foo in foos:
            if foo.id in self.foo_extra_values:
                self.assertEquals(foo.extra.extra_info,
                        self.foo_extra_values[foo.id])
                self.assertEquals(foo.extra.foo, foo)
            else:
                self.assertEquals(foo.extra, None)
        foo_extras = FooExtra.query().join("foo").execute(self.cursor)
        self.assertEquals(len(foo_extras), len(self.foo_extra_values))
        for extra in foo_extras:
            self.assertEquals(extra.foo.id, extra.id)

    def test_subquery(self):
        foos = Foo.query_with_counts().execute(self.cursor)
        for foo in foos:
            categories = self.foo_to_categories.get(foo.id, [])
            self.assertEquals(foo.category_count, len(categories))
            bars = self.foo_to_bars.get(foo.id, [])
            self.assertEquals(foo.bar_count, len(bars))

    def test_subquery_filter(self):
        query = Foo.query_with_counts()
        query.filter(query.c.category_count > 2)
        foos = query.execute(self.cursor)
        for foo in foos:
            self.assert_(foo.category_count > 2)

    def test_subquery_orderby(self):
        query = Foo.query_with_counts().order_by('bar_count')
        results = query.execute(self.cursor)
        for i in range(len(results) - 1):
            self.assert_(results[i].bar_count <= results[i+1].bar_count)

    def test_multiple_join(self):
        foos = Foo.query().join('categories', 'bars').execute(self.cursor)
        for foo in foos:
            self.check_categories(foo)
            self.check_bars(foo)

    def test_deep_join(self):
        query = Bar.query().join('parent', 'parent.categories')
        for bar in query.execute(self.cursor):
            self.check_bar_parent(bar)
            self.check_categories(bar.parent)

    def test_join_to_get(self):
        foo = Foo.get(self.cursor, 2, join='bars')
        self.check_bars(foo)

    def test_join_to_results(self):
        foos = Foo.query().execute(self.cursor)
        foos.join('bars').execute(self.cursor)
        for foo in foos:
            self.check_bars(foo)
        self.checkFoos(foos, self.foo_values)

    def test_join_to_record(self):
        foo = Foo.get(self.cursor, 2)
        foo.join("bars").execute(self.cursor)
        self.check_bars(foo)

    def test_join_twice(self):
        foo = Foo.get(self.cursor, 2)
        foo.join("bars").execute(self.cursor)
        join = foo.join("bars")
        self.assert_(join.no_joins())
        join.execute(self.cursor)

    def test_join_to_results_multiple_primary_keys(self):
        query = CategoryMap.query()
        query.filter(CategoryMap.c.foo_id.in_([1,2]))
        results = query.execute(self.cursor)
        results.join('category', 'foo').execute(self.cursor)
        seen_ids = []
        for record in results:
            seen_ids.append((record.foo.id, record.category.id))
        correct_ids = [(1, value) for value in self.foo_to_categories[1]]
        correct_ids += [(2, value) for value in self.foo_to_categories[2]]
        self.assertSameSet(seen_ids, correct_ids)

    def test_join_with_filter(self):
        query = Bar.query().join('parent')
        query.joins.parent.filter(id=1)
        correct_ids = []
        for id, foo_id, name in self.bar_values:
            if foo_id == 1:
                correct_ids.append(id)
        self.assertEquals(query.count(self.cursor), len(correct_ids))
        returned_ids = [bar.id for bar in query.execute(self.cursor)]
        self.assertSameSet(correct_ids, returned_ids)
        query2 = Bar.query().join('parent')
        query2.filter(query2.joins.parent.c.id == 1)
        self.assertEquals(str(query), str(query2))

    def test_on_restore(self):
        def fake_on_restore(self):
            self.on_restore_called = True
        Foo.on_restore = fake_on_restore
        try:
            foo = Foo.get(self.cursor, 1)
            self.assert_(hasattr(foo, 'on_restore_called'))
        finally:
            del Foo.on_restore
