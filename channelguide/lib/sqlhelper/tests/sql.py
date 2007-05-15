from base import TestCase
from sqlhelper import sql
from sqlhelper.sql import clause

class SelectTest(TestCase):
    def test_select(self):
        s = sql.Select()
        s.add_columns('foo.id', 'foo.name')
        s.add_from("foo")
        self.assertSameSet(s.execute(self.cursor), self.foo_values)

    def test_where(self):
        select = sql.Select()
        select.add_columns('foo.id', 'foo.name')
        select.add_from('foo')
        select.add_where(clause.Where('id=%s', [2]) | 
                clause.Where('id=%s', [3]))
        matched_values = [(id, name) for id, name in self.foo_values 
            if id in (2,3)]
        self.assertSameSet(select.execute(self.cursor), matched_values)

    def get_by_id(self, id):
        select = sql.Select()
        select.add_columns('foo.id', 'foo.name')
        select.add_from('foo')
        select.add_where('id=%s', id)
        return select.execute(self.cursor)[0]

    def test_insert(self):
        insert = sql.Insert('foo')
        insert.add_value('id', 500)
        insert.add_value("name", 'bigbird')
        insert.execute(self.cursor)
        row = self.get_by_id(500)
        self.assertEquals(row[1], 'bigbird')

    def test_update(self):
        update = sql.Update('foo')
        update.add_where('id=%s', 2)
        update.add_value('name', 'daffy duck')
        update.execute(self.cursor)
        row = self.get_by_id(2)
        self.assertEquals(row[1], 'daffy duck')

    def test_delete(self):
        delete = sql.Delete('foo')
        delete.add_where('id > 3')
        delete.execute(self.cursor)
        select = sql.Select()
        select.add_columns('foo.id')
        select.add_from('foo')
        for row in select.execute(self.cursor):
            self.assert_(row[0] <= 3)
