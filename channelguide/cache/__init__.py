"""Cache for the channelguide.

Here's our cache strategy:

* We store entire response objects in the cache.
* We store a create a cache key based on the following pieces of data:
  path, query, COOKIE header.
* We only cache GET requests
* Some views depend on tables, and are invalidated when the tables change
"""
from client import clear_cache
import dbwatcher
from record import CachedRecord
from decorators import aggresively_cache, cache_page_externally_for
