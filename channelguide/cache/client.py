import memcache
from django.conf import settings
from threading import Lock

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

memcache_client_lock = Lock()

def set(key, value, time=0):
    key = settings.CACHE_PREFIX + key
    memcache_client_lock.acquire()
    try:
        return memcache_client.set(key, value, time)
    finally:
        memcache_client_lock.release()

def set_multi(mapping, time=0):
    memcache_client_lock.acquire()
    try:
        return memcache_client.set_multi(mapping, time,
                key_prefix=settings.CACHE_PREFIX)
    finally:
        memcache_client_lock.release()

def get(key):
    key = settings.CACHE_PREFIX + key
    memcache_client_lock.acquire()
    try:
        return memcache_client.get(key)
    finally:
        memcache_client_lock.release()

def get_multi(keys):
    memcache_client_lock.acquire()
    try:
        return memcache_client.get_multi(keys,
                key_prefix=settings.CACHE_PREFIX)
    finally:
        memcache_client_lock.release()

def delete(key):
    key = settings.CACHE_PREFIX + key
    memcache_client_lock.acquire()
    try:
        return memcache_client.delete(key)
    finally:
        memcache_client_lock.release()

def incr(key, delta=1):
    key = settings.CACHE_PREFIX + key
    memcache_client_lock.acquire()
    try:
        return memcache_client.incr(key, delta)
    finally:
        memcache_client_lock.release()

def clear_cache():
    memcache_client_lock.acquire()
    try:
        memcache_client.flush_all()
    finally:
        memcache_client_lock.release()
