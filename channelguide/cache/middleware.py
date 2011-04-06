
# See LICENSE for details.

import time
from django.conf import settings
from django.core import cache

from channelguide import util
from channelguide.guide.country import country_code

try:
    from mongo_stats.middleware import MongoStatsMiddleware
except ImportError:
    pass
else:
    class CacheTimingMiddleware(MongoStatsMiddleware):
        def request_was_cached(self, request):
            if hasattr(request, '_cache_hit'):
                return True # our cache middleware
            return MongoStatsMiddleware.request_was_cached(self, request)

class CacheMiddlewareBase(object):
    cache_time = settings.CACHE_MIDDLEWARE_SECONDS # how many seconds to cache
                                                   # for
    namespace = 'namespace'

    def __init__(self, namespace=None):
        if namespace is not None:
            # used to separately cache search pages
            self.namespace = namespace

    def get_cache_key_tuple(self, request):
        """Return a tuple that will be used to create the cache key."""
        if not isinstance(self.namespace, tuple):
            namespace_names = (self.namespace,)
        else:
            namespace_names = self.namespace
        namespace_values = cache.cache.get_many(namespace_names)
        for name in namespace_names:
            if type(namespace_values.get(name, None)) is not float:
                namespace_values[name] = None
            if namespace_values.get(name, None) is None:
                namespace_values[name] = time.time()
                cache.cache.set(name, namespace_values[name])
        return tuple([namespace_values[k] for k in namespace_names]) + (
            request.LANGUAGE_CODE,)

    def response_to_cache_object(self, request, response):
        return response

    def response_from_cache_object(self, request, cached_object):
        return cached_object

    def get_cache_key(self, request):
        prefix = self.__class__.__name__ + ":"
        tuple = self.get_cache_key_tuple(request)
        return prefix + hex(hash(tuple))

    def can_cache_request(self, request):
        return (request.method == 'GET' and
                'no-cache' not in request.META.get('HTTP_CACHE_CONTROL', ''))

    def process_request(self, request):
        if not self.can_cache_request(request):
            return None
        key = self.get_cache_key(request)
        cached_object = cache.cache.get(key)
        if cached_object is None:
            return None
        else:
            response = self.response_from_cache_object(request, cached_object)
            request._cache_hit = response._cache_hit = True
            return response

    def process_response(self, request, response):
        if (request.method == 'GET' and response.status_code == 200 and
                not hasattr(request, '_cache_hit')):
            key = self.get_cache_key(request)
            cache.cache.set(key,
                    self.response_to_cache_object(request, response),
                    self.cache_time)
        return response

class UserCacheMiddleware(CacheMiddlewareBase):
    """
    Caches a page that's different for each user.  Useful for pages
    that have ratings.
    """
    def get_cache_key_tuple(self, request):
        filter_languages = ''
        if request.user.is_authenticated():
            user = request.user.username
            profile = request.user.get_profile()
            if profile.filter_languages:
                filter_languages = ''.join(
                    [lang.name for lang in profile.shown_languages.all()])
        else:
            user = None
            if request.session.get('filter_languages'):
                filter_languages = request.LANGUAGE_CODE
        return CacheMiddlewareBase.get_cache_key_tuple(self, request) + (
            request.path, request.META['QUERY_STRING'], user, filter_languages)

class SiteHidingCacheMiddleware(UserCacheMiddleware):
    """
    This middleware caches pages which might hide sites from old Miro users or
    Miro users on Linux.
    """
    def get_cache_key_tuple(self, request):
        # XXX to a certain extent, this is copied from
        # XXX channelguide/guide/views/channels.py:filtered_listing
        miro_version_pre_sites = miro_linux = False
        miro_version = util.get_miro_version(
            request.META.get('HTTP_USER_AGENT'))
        if miro_version and int(miro_version.split('.')[0]) < 2:
            miro_version_pre_sites = True
        if miro_version and 'X11' in request.META.get('HTTP_USER_AGENT', ''):
            miro_linux = True

        geoip = request.GET.get('geoip', None)
        if geoip != 'off':
            geoip = country_code(request)
        else:
            geoip = None


        return UserCacheMiddleware.get_cache_key_tuple(self, request) + (
            miro_version_pre_sites, miro_linux, geoip)


class APICacheMiddleware(CacheMiddlewareBase):

    def get_cache_key_tuple(self, request):
        if request.user.is_authenticated():
            user = request.user.id
        else:
            user = None
        # since we're not doing any translating in the API, we can ignore the
        # LANGUAGE_CODE
        GET_args = dict(request.GET)
        if 'jsoncallback' in GET_args:
            del GET_args['jsoncallback']
        if '_' in GET_args:
            del GET_args['_']
        return CacheMiddlewareBase.get_cache_key_tuple(self, request)[:-1] + \
            (request.path, str(GET_args), user)

    def response_to_cache_object(self, request, response):
        if request.GET.get('datatype') == 'json' and \
                'jsoncallback' in request.GET:
            response.content = response.content[
                len(request.GET['jsoncallback'])+1:-2]
        return response

    def response_from_cache_object(self, request, response):
        if request.GET.get('datatype') == 'json' and \
                'jsoncallback' in request.GET:
            response.content = '%s(%s);' % (
                request.GET['jsoncallback'],
                response.content)
        return response

    def process_response(self, request, response):
        response = CacheMiddlewareBase.process_response(self, request,
                                                        response)
        return self.response_from_cache_object(request, response)
