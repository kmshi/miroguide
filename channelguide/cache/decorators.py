from middleware import TableDependentCacheMiddleware, AggressiveCacheMiddleware
from django.utils.decorators import decorator_from_middleware

cache = lambda f, *args: f
aggresively_cache = decorator_from_middleware(AggressiveCacheMiddleware)

def cache_page_externally_for(seconds):
    def decorator(func):
        def inner(*args, **kwargs):
            response = func(*args, **kwargs)
            response.headers['Cache-Control'] = 'max-age=%d' % seconds
            return response
        return inner
    return decorator
