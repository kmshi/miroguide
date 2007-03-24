"""Cache for the channelguide.

Here's our cache strategy:

* We store entire response objects in the cache.
* We store a create a cache key based on the following pieces of data:
  path, query, COOKIE header.
* We only cache GET requests
* When any piece of data changes in the guide we call clear_cache which
invalidates the entire cache.
"""
import time

import memcache
from django.conf import settings
from django.core.handlers.wsgi import WSGIRequest
from django.utils.decorators import decorator_from_middleware

from channelguide import util

memcache_client = memcache.Client(settings.MEMCACHED_SERVERS)
memcache_client.flush_all()
time.sleep(1) # hack so that the flush_all happens
disable_cache = False

def get_cache_key(request):
    try:
        return hex(hash((request.path, request.META['QUERY_STRING'],
            request.META.get('HTTP_COOKIE'))))
    except TypeError:
        # Maybe this is the test browser, which sends the HTTP_COOKIE value as
        # an actual dict
        if type(request) is WSGIRequest:
            return hex(hash((request.path, request.META['QUERY_STRING'],
                request.META['HTTP_COOKIE'].output())))
        else:
            raise

def clear_cache():
    memcache_client.flush_all()

def cache_externally_for(response, seconds):
    response.headers['Cache-Control'] = 'max-age=%d' % seconds

class CacheMiddleware(object):
    def process_request(self, request):
        request._cache_update_cache = False
        if request.method != 'GET':
            return None

        cached_response = memcache_client.get(get_cache_key(request))
        if cached_response is None or disable_cache:
            request._cache_update_cache = True
            return None
        else:
            return cached_response

    def process_response(self, request, response):
        if 'Cache-Control' not in response.headers:
            response.headers['Cache-Control'] = 'max-age=0'
        if not request._cache_update_cache:
            return response
        if response.status_code != 200:
            return response
        memcache_client.set(get_cache_key(request), response)
        return response

def cache_page_externally_for(seconds):
    def decorator(func):
        def inner(*args, **kwargs):
            response = func(*args, **kwargs)
            cache_externally_for(response, seconds)
            return response
        return inner
    return decorator
