from sqlalchemy import MapperExtension

from client import clear_cache

clear_cache_exceptions = set()
def dont_clear_cache_for(class_):
    """When objects of this class change, we don't need to clear the cache."""
    clear_cache_exceptions.add(class_)

class CacheClearMapperExtension(MapperExtension):
    def handle_change(self, mapper, connection, instance):
        if instance.__class__ not in clear_cache_exceptions:
            clear_cache()

    def after_insert(self, mapper, connection, instance):
        self.handle_change(mapper, connection, instance)

    def after_delete(self, mapper, connection, instance):
        self.handle_change(mapper, connection, instance)

    def after_update(self, mapper, connection, instance):
        self.handle_change(mapper, connection, instance)
