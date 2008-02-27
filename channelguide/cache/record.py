# Copyright (c) 2008 Participatory Culture Foundation
# See LICENSE for details.

from sqlhelper.orm import Record
from channelguide import util
from channelguide.cache import client
class CachedRecord(Record):

    @classmethod
    def cache_prefix(cls, key_values):
        key_string = ':'.join([str(k) for k in key_values])
        return '%s:%s:' % (cls.__name__, key_string)

    @classmethod
    def load_from_cache(cls, key_values, other_keys=None):
        if not isinstance(key_values, (tuple, list)):
            key_values = (key_values, )
        if other_keys is None:
            other_keys = []
        cache_key_prefix = cls.cache_prefix(key_values)
        keys_to_load = [cache_key_prefix+key for key in ['object'] + other_keys]
        dictionary = client.get_multi(keys_to_load)
        if dictionary is None or len(dictionary) != len(keys_to_load):
            return
        obj = cls()
        obj.__dict__ = dictionary[cache_key_prefix + 'object']
        for key in other_keys:
            setattr(obj, key, dictionary[cache_key_prefix + key])
        obj.on_restore()
        return obj

    @classmethod
    def get(cls, connection, id, load=None, join=None):
        if load is not None:
            load = util.ensure_list(load)
        else:
            load = []
        if join is not None:
            join = util.ensure_list(join)
        else:
            join = []
        obj = cls.load_from_cache(id)
        if obj is None:
            # couldn't load from cache
            obj = super(CachedRecord, cls).get(connection, id, load, join)
            obj.save_to_cache()
            return obj
        else:
            print 'from cache'
            if load or join:
                if load:
                    obj = obj.load(*load)
                if join:
                    obj = obj.join(*join)
                print obj
                obj = obj.execute(connection)
            return obj

    def save_to_cache(self):
        self.set_foreign_keys_from_relations()
        key_values = self.primary_key_values()
        cache_key_prefix = self.cache_prefix(key_values)
        d = self.__dict__.copy()
        column_names = [col.name for col in self.table.concrete_columns()]
        column_names.append('rowid')
        erase_keys = [k for k in d if k not in column_names]
        for k in erase_keys:
            del d[k]
        return client.set(cache_key_prefix + 'object', d)

    def __eq__(self, other):
        if type(other) != type(self):
            return NotImplemented
        for col in self.table.concrete_columns():
            if getattr(self, col.name) != getattr(other, col.name):
                return False
        return True

    def insert(self, connection):
        Record.insert(self, connection)
        self.save_to_cache()

    def update(self, connection):
        Record.update(self, connection)
        self.save_to_cache()



