"""Add hooks so when we change anything in the DB we clear the cache."""

from sqlalchemy import MapperExtension, EXT_PASS

from channelguide import cache

class CacheClearer(MapperExtension):
    def after_insert(self, mapper, connection, instance):
        cache.clear_cache()

    def after_delete(self, mapper, connection, instance):
        cache.clear_cache()

    def after_update(self, mapper, connection, instance):
        cache.clear_cache()
