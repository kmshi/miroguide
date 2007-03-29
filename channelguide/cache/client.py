import memcache
from django.conf import settings

class FakeClient(object):
    def get(self, key):
        return None

    def set(self, key, value):
        pass

    def flush_all(self):
        pass

if settings.MEMCACHED_SERVERS:
    memcache_client = memcache.Client(settings.MEMCACHED_SERVERS)
else:
    memcache_client = FakeClient()

def clear_cache():
    memcache_client.flush_all()
