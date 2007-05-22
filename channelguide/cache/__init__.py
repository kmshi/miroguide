"""Cache for the channelguide.

Here's our cache strategy:

* We store entire response objects in the cache.
* We store a create a cache key based on the following pieces of data:
  path, query, COOKIE header.
* We only cache GET requests
* When any piece of data changes in the guide we call clear_cache which
invalidates the entire cache.
"""
from client import clear_cache
from dbwatcher import dont_clear_cache_for
from decorators import aggresively_cache, cache_page_externally_for
