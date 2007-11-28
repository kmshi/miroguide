from channelguide.cache import client as cache_client
from sqlhelper.orm import Record

class MemoryRecord(Record):

    default_joins = None

    @classmethod
    def _get_records_from_cache(cls, ids):
        keys = [cls._cache_key(id) for id in ids]
        return cache_client.get_multi(keys)

    @classmethod
    def _get_records_from_db(cls, connection, ids):
        query = cls.query().join(*cls.default_joins)
        query.where(cls.c.id.in_(ids))
        for channel in query.execute(connection):
#            channel.from_db()
            yield channel

    @classmethod
    def _cache_key(cls, id):
        return 'object:%s:%s' % (cls.__name__, id)

    @classmethod
    def get(cls, connection, id, join=None):
        if isinstance(id, (list, tuple)):
            if len(id) > 1:
                raise RuntimeError, "id length > 1: %i" % len(id)
            id = id[0]
        channel = cls._get_records_from_cache([id])
        if join:
            for j in join:
                if j not in cls.default_joins:
                    raise ValueError, "invalid join: %s" % j
        if channel:
            return channel.itervalues().next()
        else:
            try:
                record = cls._get_records_from_db(connection, [id]).next()
            except StopIteration:
                raise LookupError
            else:
                record.update_cache()
                return record

    def update_cache(self):
        key = self._cache_key(self.id)
        cache_client.set(key, self)

    def insert(self, connection):
        super(MemoryRecord, self).insert(connection)
        new = super(MemoryRecord, self).get(connection, self.primary_key_values(),
                join=self.default_joins)
        for join_name in self.default_joins:
            setattr(self, join_name, getattr(new, join_name))
        self.update_cache()

    def update(self, connection):
        self.update_cache()
        super(MemoryRecord, self).update(connection)

    def from_db(self):
        """
        Called when an object is loaded from the database.
        """
