# Copyright (c) 2009 Participatory Culture Foundation
# See LICENSE for details.

try:
    import pymongo
except ImportError:
    pymongo = None

import time, datetime
from django.conf import settings

class MongoStatsMiddleware(object):

    def __init__(self):
        if not pymongo:
            return
        try:
            self.connection = pymongo.Connection(
                getattr(settings, 'MONGO_HOST', 'localhost'),
                getattr(settings, 'MONGO_PORT', 27017))
        except pymongo.errors.ConnectionFailure:
            self.connection = self.collection = None
        else:
            db = self.connection[settings.MONGO_STATS_DATABASE]
            self.collection = db[settings.MONGO_STATS_COLLECTION]

    def process_request(self, request):
        if not pymongo:
            return
        request.start_time = time.time()

    def process_view(self, request, view_func, view_args, view_kwargs):
        request.view_func = "%s.%s" % (view_func.__module__,
                                       view_func.func_name)
        request.view_args = view_args
        request.view_kwargs = view_kwargs
        return

    def request_was_cached(self, request):
        if (hasattr(request, '_cache_update_cache') and
            request._cache_update_cache == False and
            request.method in ('GET', 'HEAD') and
            not request.GET and
            request.user.is_anonymous()):
            return True
        return False

    def process_response(self, request, response):
        if not hasattr(request, 'start_time'):
            return response
        if self.collection is None:
            return response
        timestamp = time.time()
        total = timestamp - request.start_time
        doc = {
            'time': datetime.datetime.utcnow(),
            'timestamp': timestamp,
            'total': total,
            'status_code': response.status_code,
            'headers': dict(response._headers.values()),
            'encoding': request.encoding or settings.DEFAULT_CHARSET,
            'method': request.method,
            'cached?': bool(self.request_was_cached(request)),
            'authenticated?': bool(request.user.is_authenticated()),
            'secure?': request.is_secure(),
            'ajax?': request.is_ajax(),
            'host': request.get_host(),
            'path': request.path,
            'GET': dict(request.GET),
            'POST': dict(request.POST),
            'META': dict((k, v) for k, v in request.META.items()
                         if not k.startswith('wsgi.')),
            'raw_post_data': pymongo.binary.Binary(request.raw_post_data),
            'view_func': getattr(request, 'view_func', ''),
            'view_args': list(getattr(request, 'view_args', [])),
            'view_kwargs': getattr(request, 'view_kwargs', {})
            }
        self.collection.insert(doc)
        return response
