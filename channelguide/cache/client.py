import memcache
from django.conf import settings

memcache_client = memcache.Client(settings.MEMCACHED_SERVERS)

def clear_cache():
    memcache_client.flush_all()
