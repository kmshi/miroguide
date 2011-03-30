# Copyright (c) 2008 Participatory Culture Foundation
# See LICENSE for details.

from middleware import UserCacheMiddleware
from middleware import SiteHidingCacheMiddleware, APICacheMiddleware
from django.utils.decorators import (decorator_from_middleware,
                                     decorator_from_middleware_with_args)

cache_with_sites = decorator_from_middleware_with_args(
    SiteHidingCacheMiddleware)
cache_for_user = decorator_from_middleware(UserCacheMiddleware)
api_cache = decorator_from_middleware(APICacheMiddleware)
