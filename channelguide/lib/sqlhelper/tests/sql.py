from base import TestCase
from sqlhelper import sql

class SelectTest(TestCase):
    def test_select(self):
        s = sql.Select('foo.id', 'foo.name')
        s.froms.append('foo')
        self.assertSameSet(s.execute(self.connection), self.foo_values)

    def test_where(self):
        select = sql.Select('foo.id')
        select.columns.append(sql.Expression('foo.name'))
        select.froms.append('foo')
        select.wheres.append(sql.Expression('id=%s', 2) | 
                sql.Expression('id=%s', 3))
        matched_values = [(id, name) for id, name in self.foo_values 
            if id in (2,3)]
        self.assertSameSet(select.execute(self.connection), matched_values)

    def test_group_by(self):
        select = sql.Select('foo.id', 'MIN(bar.name) AS first_bar')
        select.froms.append(sql.Join('foo', 'bar', 'bar.foo_id=foo.id'))
        select.group_by.append('foo.id')
        correct = []
        for id, bars in self.foo_to_bars.items():
            first_bar = min(name for (id, foo_id, name) in bars)
            correct.append((id, first_bar))
        self.assertSameSet(select.execute(self.connection), correct)

    def test_expression(self):
        expression = sql.Expression('id * id').label('id_squared')
        select = sql.Select('id', expression)
        select.froms.append('foo')
        select.order_by.append('id_squared')
        last_row = None
        for row in select.execute(self.connection):
            self.assertEquals(row[1], row[0] * row[0])
            if last_row:
                self.assert_(last_row[1] <= row[1])
            last_row = row

    def test_join(self):
        select = sql.Select('foo.id', 'bar.id')
        join = sql.Join('foo', 'bar', 'foo.id=bar.foo_id', 'LEFT')
        select.froms.append(join)
        correct_rows = [ (1, 1), (1, 2), (2, 3), (3, 4), (4, None), (5, None)]
        self.assertSameSet(correct_rows, select.execute(self.connection))

    def test_subquery(self):
        select = sql.Select('foo.id', 'subquery.maxname')
        max_name = sql.Select('foo_id, MAX(bar.name) AS maxname')
        max_name.froms.append('bar')
        max_name.group_by.append('foo_id')
        subquery = max_name.subquery('subquery')
        select.froms.append(sql.Join('foo', subquery,
            'foo.id=subquery.foo_id'))
        correct_rows = [ (1, 'dog'), (2, 'tiger'), (3, 'squirel') ]
        self.assertSameSet(correct_rows, select.execute(self.connection))

    def test_scalar_subquery(self):
        select = sql.Select('foo.id')
        select.froms.append('foo')
        max_id = sql.Select('MAX(bar.id)')
        max_id.froms.append('bar')
        max_id.wheres.append('foo_id=foo.id')
        min_id = sql.Select('MIN(bar.id)')
        min_id.froms.append('bar')
        min_id.wheres.append('foo_id=foo.id')
        select.columns.append(max_id.subquery() + min_id.subquery())
        correct_rows = [ (1, 3), (2, 6), (3, 8), (4, None), (5, None)]
        self.assertSameSet(correct_rows, select.execute(self.connection))

    def test_cross_join(self):
        select = sql.Select('foo.id', 'bar.id')
        select.froms.append(sql.CrossJoin("foo", 'bar'))
        select.wheres.append('foo.id=bar.foo_id')
        correct_rows = [ (1, 1), (1, 2), (2, 3), (3, 4)]
        self.assertSameSet(correct_rows, select.execute(self.connection))


class SQLUpdateTest(TestCase):
    def get_by_id(self, id):
        select = sql.Select('foo.id', 'foo.name')
        select.froms.append('foo')
        select.wheres.append('id=%s', id)
        return select.execute(self.connection)[0]

    def test_insert(self):
        insert = sql.Insert('foo')
        insert.add_value('id', 500)
        insert.add_value("name", 'bigbird')
        insert.execute(self.connection)
        row = self.get_by_id(500)
        self.assertEquals(row[1], 'bigbird')

    def test_update(self):
        update = sql.Update('foo')
        update.wheres.append('id=%s', 2)
        update.add_value('name', 'daffy duck')
        update.execute(self.connection)
        row = self.get_by_id(2)
        self.assertEquals(row[1], 'daffy duck')

    def test_delete(self):
        delete = sql.Delete('foo')
        delete.wheres.append('id > %s', 3)
        delete.execute(self.connection)
        select = sql.Select('foo.id')
        select.froms.append('foo')
        for row in select.execute(self.connection):
            self.assert_(row[0] <= 3)
