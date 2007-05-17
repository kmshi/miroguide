from sqlhelper import signals, sql
from base import TestCase, Foo

class SignalTest(TestCase):
    def setUp(self):
        TestCase.setUp(self)
        self.signal = signals.Signal('foo', signature=[])
        self.complex_signal = signals.Signal('foo', signature=['arg'])
        self.callbacks = []

    def tearDown(self):
        for obj in dir(signals):
            if isinstance(obj, signals.Signal):
                obj.listeners = {}
        TestCase.tearDown(self)

    def callback(self, *args, **kwargs):
        self.callbacks.append((args, kwargs))

    def test_connect(self):
        self.signal.emit()
        self.assertEquals(len(self.callbacks), 0)
        self.signal.connect(self.callback)
        self.signal.emit()
        self.assertEquals(len(self.callbacks), 1)

    def test_disconnect(self):
        handle = self.signal.connect(self.callback)
        self.signal.emit()
        self.assertEquals(len(self.callbacks), 1)
        self.signal.disconnect(handle)
        self.signal.emit()
        self.assertEquals(len(self.callbacks), 1)

    def test_connect_args(self):
        self.signal.connect(self.callback, 'foo', bar='value')
        self.signal.emit()
        self.assertEquals(self.callbacks, [(('foo',), {'bar': 'value'})])

    def test_signature(self):
        self.complex_signal.connect(self.callback, 'foo')
        self.complex_signal.emit('bar')
        self.assertEquals(self.callbacks, [(('bar', 'foo'), {})])

    def test_emit(self):
        self.assertRaises(ValueError, self.complex_signal.emit)
        self.assertRaises(ValueError, self.signal.emit, 'abc')

    def test_sql_callbacks(self):
        signals.sql_insert.connect(self.callback)
        signals.sql_update.connect(self.callback)
        signals.sql_delete.connect(self.callback)

        insert = sql.Insert('foo')
        insert.add_value('id', 1000)
        insert.add_value('name', '123')
        insert.execute(self.cursor)
        update = sql.Update('foo')
        update.add_where('id=%s', 1000)
        update.add_value('name', '456')
        update.execute(self.cursor)
        delete = sql.Delete('foo')
        delete.execute(self.cursor)

        self.assertEquals(len(self.callbacks), 3)
        self.assertEquals(self.callbacks[0][0][0], insert)
        self.assertEquals(self.callbacks[1][0][0], update)
        self.assertEquals(self.callbacks[2][0][0], delete)

    def test_record_callbacks(self):
        signals.record_insert.connect(self.callback)
        signals.record_update.connect(self.callback)
        signals.record_delete.connect(self.callback)

        foo = Foo.get(self.cursor, 2)
        foo.delete(self.cursor)

        foo2 = Foo()
        foo2.name = 'ben'
        foo2.save(self.cursor)

        foo3 = Foo.get(self.cursor, 3)
        foo3.save(self.cursor)

        self.assertEquals(len(self.callbacks), 3)
        self.assertEquals(self.callbacks[0][0][0], foo)
        self.assertEquals(self.callbacks[1][0][0], foo2)
        self.assertEquals(self.callbacks[2][0][0], foo3)
