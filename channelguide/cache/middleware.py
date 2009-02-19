# Copyright (c) 2008 Participatory Culture Foundation
# See LICENSE for details.

from Cookie import SimpleCookie
import time
from django.conf import settings

import client

from channelguide import util

def date_time_string(timestamp=None):
    """return the current date and time formatted for a message header."""
    if timestamp is None:
        timestamp = time.time()
    timetuple = time.gmtime(timestamp)
    s = time.strftime("%a, %02d %3b %4Y %02H:%02M:%02S gmt", timetuple)
    return s

class CacheTimingMiddleware(object):
    def process_request(self, request):
        if settings.DISABLE_CACHE:
            return
        request.start_time = time.time()

    def process_response(self, request, response):
        if not hasattr(request, 'start_time'):
            return response
        total = time.time() - request.start_time
        f = file('/tmp/page_timing', 'a')
        if hasattr(request, '_cache_hit'):
            type = 'C'
        else:
            type = 'R'
        if hasattr(request, 'user'):
            if request.user.is_authenticated():
                type = type + 'A'
        line = '%s!%s!%i!%s!%s!%f\n' % (time.asctime(),type, response.status_code, request.path, request.META.get('QUERY_STRING', ''), total)
        f.write(line.encode('utf8'))
        f.close()
        del request.start_time
        if response['Content-Type'].startswith('text/html'):
            footer = '\n<!-- %s -->' % line
            response.content = response.content + footer.encode('utf-8')
        return response

class CacheMiddlewareBase(object):
    cache_time = 0 # how many seconds to cache for
    namespace = 'namespace'
    def get_cache_key_tuple(self, request):
        """Return a tuple that will be used to create the cache key."""
        if not isinstance(self.namespace, tuple):
            namespace_names = (self.namespace,)
        else:
            namespace_names = self.namespace
        namespace_values = client.get_multi(namespace_names)
        for name in namespace_names:
            if type(namespace_values.get(name, None)) is not float:
                namespace_values[name] = None
            if namespace_values.get(name, None) is None:
                namespace_values[name] = time.time()
                client.set(name, namespace_values[name])
        return tuple([namespace_values[k] for k in namespace_names]) + (request.LANGUAGE_CODE,)

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
        if settings.DISABLE_CACHE:
            return
        if not self.can_cache_request(request):
            return None
#        lastModified = request.META.get('HTTP_IF_MODIFIED_SINCE')
#        etag = request.META.get('HTTP_IF_NONE_MATCH')
        key = self.get_cache_key(request)
#        httpKeys = {}
#        if lastModified:
#            httpKeys[key+':last_modified'] = lastModified
#        if etag:
#            httpKeys[key+':etag'] = etag
#        if client.get_multi(httpKeys.keys()) == httpKeys: # same file as before
#            request._cache_hit = True
#            return HttpResponseNotModified()
        cached_object = client.get(key)
        if cached_object is None:
            return None
        else:
            response = self.response_from_cache_object(request, cached_object)
            request._cache_hit = response._cache_hit = True
            return response

    def process_response(self, request, response):
        if not response.has_header('Cache-Control'):
            response['Cache-Control'] = 'max-age=0'
        if (request.method == 'GET' and response.status_code == 200 and
                not hasattr(request, '_cache_hit') and
                not settings.DISABLE_CACHE):
            key = self.get_cache_key(request)
            client.set(key,
                    self.response_to_cache_object(request, response),
                    time=self.cache_time)
#            etag = md5.new(response.content).hexdigest()
#            client.set(key+':etag', etag)
#            lastModified = date_time_string()
#            client.set(key+':last_modified', lastModified)
#            response.headers['ETag'] = etag
#            response.headers['Last-Modified'] = date_time_string()
        return response


class CacheMiddleware(CacheMiddlewareBase):

    def get_cache_key_tuple(self, request):
        parent = CacheMiddlewareBase.get_cache_key_tuple(self, request)
        cookie = request.META.get('HTTP_COOKIE')
        if type(cookie) is SimpleCookie:
            # Maybe this is the test browser, which sends the HTTP_COOKIE
            # value as an python Cookie object
            return parent + (request.path, request.META['QUERY_STRING'],
                    cookie.output())
        else:
            return parent + (request.path, request.META['QUERY_STRING'], cookie)

class TableDependentCacheMiddleware(CacheMiddlewareBase):

    def __init__(self, *tables):
        self.table_keys = ['Table:' + (hasattr(t, 'name') and t.name or t)
                for t in tables]

    def get_cache_key(self, request):
        cache_key = CacheMiddlewareBase.get_cache_key(self, request)
        if not getattr(self, 'table_keys', None):
            return cache_key
        ret = client.get_multi(self.table_keys)
        if len(ret) != len(self.table_keys):
            for k in (key for key in self.table_keys if key not in ret):
                v = time.time()
                client.set(k, v)
                ret[k] = v
        appends = ['%s' % ret[k] for k in self.table_keys]
        key = cache_key + ':' + ':'.join(appends)
        return key

class UserCacheMiddleware(CacheMiddlewareBase):
    """
    Caches a page that's different for each user.  Useful for pages
    that have ratings.
    """
    def get_cache_key_tuple(self, request):
        if request.user.is_authenticated():
            user = request.user.username
        else:
            user = None
        return CacheMiddlewareBase.get_cache_key_tuple(self, request) + (request.path, request.META['QUERY_STRING'], user)

class AggressiveCacheMiddleware(UserCacheMiddleware):
    """Aggresively Caches a page.  This should only be used for pages that
     * Don't use any session data, or any cookie data
     * Are displayed the same for each user (except the account bar)
     * Don't do any authentication

    This middleware caches pages without regard to the cookies.  When a
    request is about to be processed, if there is a page in the cache, it uses
    that page, but replaces the account bar with a newly generated account
    bar.
    """

    account_bar_start = '<!-- START ACCOUNT BAR -->'
    account_bar_end = '<!-- END ACCOUNT BAR -->'

    def __init__(self, namespace=None):
        UserCacheMiddleware.__init__(self)
        if namespace:
            self.namespace = namespace
    """
    def get_cache_key_tuple(self, request):
        if request.user.is_authenticated():
            user = request.user.username
        else:
            user = None
        return CacheMiddlewareBase.get_cache_key_tuple(self, request) + (request.path, request.META['QUERY_STRING'], user)

    def response_from_cache_object(self, request, cached_response):
        t = loader.get_template("guide/account-bar.html")
        # sometimes new_account_bar is of type
        # django.utils.safestring.SafeString
        # if there are problems here, it's probably because of that
        new_account_bar = t.render(Context({'user': request.user})).encode('utf8')
        content = cached_response.content
        start = content.find(self.account_bar_start)
        head = content[:start]
        end = content.find(self.account_bar_end, start) + len(self.account_bar_end)
        tail = content[end:]
        cached_response.content = head
        cached_response.content += new_account_bar
        cached_response.content += tail
        return cached_response"""


class SiteHidingCacheMiddleware(AggressiveCacheMiddleware):
    """
    This middleware caches pages which might hide sites from old Miro users or
    Miro users on Linux.
    """
    def get_cache_key_tuple(self, request):
        # XXX to a certain extent, this is copied from
        # XXX channelguide/guide/views/channels.py:filtered_listing
        miro_version_pre_sites = miro_linux = False
        miro_version = util.get_miro_version(request.META.get('HTTP_USER_AGENT'))
        if miro_version and int(miro_version.split('.')[0]) < 2:
            miro_version_pre_sites = True
        if miro_version and 'X11' in request.META.get('HTTP_USER_AGENT', ''):
            miro_linux = True

        return UserCacheMiddleware.get_cache_key_tuple(self, request) + (
            miro_version_pre_sites, miro_linux)
