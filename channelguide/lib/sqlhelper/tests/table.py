from sqlhelper import sql
from base import TestCase, foo_table, foo_extra_table

class TableTest(TestCase):
    def test_select(self):
        rows = foo_table.select().execute(self.connection)
        self.assertSameSet(self.foo_values, rows)

    def test_select_count(self):
        count = foo_table.select_count().execute(self.connection)[0][0]
        self.assertEquals(len(self.foo_values), count)

    def test_join(self):
        select = sql.Select()
        select.add_from(foo_extra_table.join(foo_table))
        select.add_columns('foo_extra.id', 'foo_extra.extra_info', 'foo.name')
        rows = select.execute(self.connection)
        correct_rows = []
        for id, value in self.foo_values:
            if id in self.foo_extra_values:
                correct_rows.append((id, self.foo_extra_values[id], value))

        self.assertSameSet(correct_rows, rows)
