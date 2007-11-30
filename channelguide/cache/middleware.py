from Cookie import SimpleCookie
import time, md5, logging
from django.conf import settings
from django.http import HttpResponseNotModified
from django.core.handlers.wsgi import WSGIRequest
from django.template import Context, loader

import client

def date_time_string(timestamp=None):
    """return the current date and time formatted for a message header."""
    if timestamp is None:
        timestamp = time.time()
    timetuple = time.gmtime(timestamp)
    s = time.strftime("%a, %02d %3b %4Y %02H:%02M:%02S gmt", timetuple)
    return s

class CacheTimingMiddleware(object):
    def process_request(self, request):
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
        line = '%s!%s!%i!%s!%s!%f\n' % (time.asctime(),type, response.status_code, request.path, request.META.get('QUERY_STRING', ''), total)
        f.write(line)
        f.close()
        del request.start_time
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
        return tuple([namespace_values[k] for k in namespace_names])

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
        if 'Cache-Control' not in response.headers:
            response.headers['Cache-Control'] = 'max-age=0'
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

class AggressiveCacheMiddleware(CacheMiddlewareBase):
    """Aggresively Caches a page.  This should only be used for pages that
     * Don't use any session data, or any cookie data
     * Are displayed the same for each user (except the account bar)
     * Don't do any authentication

    This middleware caches pages without regard to the cookies.  When a
    request is about to be processed, if there is a page in the cache, it uses
    that page, but replaces the account bar with a newly generated account
    bar.  If adult_differs is True, the cache will also differentiate based
    on the value of the adult_ok flag of the user.
    """

    account_bar_start = '<!-- START ACCOUNT BAR -->'
    account_bar_end = '<!-- END ACCOUNT BAR -->'

    def __init__(self, namespace=None, adult_differs=False):
        CacheMiddlewareBase.__init__(self)
        if namespace:
            self.namespace = namespace
        self.adult_differs = adult_differs

    def get_cache_key_tuple(self, request):
        key_tuple = CacheMiddlewareBase.get_cache_key_tuple(self, request) + (request.path, request.META['QUERY_STRING'])
        if self.adult_differs:
            return key_tuple + (request.user.adult_ok,)
        else:
            return key_tuple

    def response_from_cache_object(self, request, cached_response):
        t = loader.get_template("guide/account-bar.html")
        new_account_bar = t.render(Context({'user': request.user})).encode('utf8')
        content = cached_response.content
        start = content.find(self.account_bar_start)
        head = content[:start]
        end = content.find(self.account_bar_end, start) + len(self.account_bar_end)
        tail = content[end:]
        if type(cached_response.content) != type(new_account_bar) != str:
            logging.info(type(cached_response.content))
            logging.info(type(new_account_bar))
        cached_response.content = head
        cached_response.content += new_account_bar
        cached_response.content += tail
        return cached_response
