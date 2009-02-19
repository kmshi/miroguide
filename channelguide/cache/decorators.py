# Copyright (c) 2008 Participatory Culture Foundation
# See LICENSE for details.

from middleware import AggressiveCacheMiddleware, UserCacheMiddleware, SiteHidingCacheMiddleware
from django.utils.decorators import decorator_from_middleware

aggresively_cache = decorator_from_middleware(AggressiveCacheMiddleware)
cache_with_sites = decorator_from_middleware(SiteHidingCacheMiddleware)
cache_for_user = decorator_from_middleware(UserCacheMiddleware)

def cache_page_externally_for(seconds):
    def decorator(func):
        def inner(*args, **kwargs):
            response = func(*args, **kwargs)
            response['Cache-Control'] = 'max-age=%d' % seconds
            return response
        return inner
    return decorator
