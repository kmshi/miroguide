from Cookie import SimpleCookie

from django.conf import settings
from django.core.handlers.wsgi import WSGIRequest
from django.template import Context, loader

import client

class CacheMiddlewareBase(object):
    def get_cache_key_tuple(self, request): 
        """Return a tuple that will be used to create the cache key."""
        raise NotImplementedError

    def response_to_cache_object(self, request, response):
        return response

    def response_from_cache_object(self, request, cached_object):
        return cached_object

    def get_cache_key(self, request): 
        prefix = self.__class__.__name__ + ":"
        return prefix + hex(hash(self.get_cache_key_tuple(request)))

    def can_cache_request(self, request):
        return (request.method == 'GET' and
                'no-cache' not in request.META.get('HTTP_CACHE_CONTROL', ''))

    def process_request(self, request):
        if not self.can_cache_request(request):
            return None
        cached_object = client.get(self.get_cache_key(request))
        if cached_object is None or settings.DISABLE_CACHE:
            return None
        else:
            request._cache_hit = True
            return self.response_from_cache_object(request, cached_object)

    def process_response(self, request, response):
        if 'Cache-Control' not in response.headers:
            response.headers['Cache-Control'] = 'max-age=0'
        if (request.method == 'GET' and response.status_code == 200 and 
                not hasattr(request, '_cache_hit')):
            client.set(self.get_cache_key(request), 
                    self.response_to_cache_object(request, response))
        return response

class CacheMiddleware(CacheMiddlewareBase):
    def get_cache_key_tuple(self, request):
        cookie = request.META.get('HTTP_COOKIE')
        if type(cookie) is SimpleCookie:
            # Maybe this is the test browser, which sends the HTTP_COOKIE
            # value as an python Cookie object
            return (request.path, request.META['QUERY_STRING'],
                    cookie.output())
        else:
            return (request.path, request.META['QUERY_STRING'], cookie)

class AggressiveCacheMiddleware(CacheMiddlewareBase):
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

    def get_cache_key_tuple(self, request): 
        return (request.path, request.META['QUERY_STRING'])

    def response_from_cache_object(self, request, cached_response):
        print repr(cached_response)
        t = loader.get_template("guide/account-bar.html")
        new_account_bar = t.render(Context({'user': request.user}))
        start = cached_response.content.find(self.account_bar_start)
        head = cached_response.content[:start] +' <!-- START REPLACEMENT %s -->' % start
        end = cached_response.content.find(self.account_bar_end, start) + len(self.account_bar_end)
        tail = '<!-- END REPLACEMENT %i --> ' % end + cached_response_content[end:]
        cached_response.content = head + new_account_bar + tail
        return cached_response
