# Copyright (c) 2009 Participatory Culture Foundation
# See LICENSE for details.

try:
    import pymongo
except ImportError:
    pymongo = None
else:
    from pymongo import bson, errors

import time, datetime
from django.conf import settings

def _fix_dict(d):
    """
    Strip out non-BSON-able keys/values from dictionaries.
    """
    new_d = {}
    for k, v in d.items():
        new_d[k.replace('.', '_').lstrip('$')] = _fix_values([v])[0]
    return new_d

def _fix_values(l):
    """
    Strip out non-BSON-able values from lists.
    """
    l = list(l)
    for index, item in enumerate(l):
        if isinstance(item, (list, tuple)):
            l[index] = _fix_values(item)
        elif isinstance(item, dict):
            l[index] = _fix_dict(item)
        else:
            try:
                bson._element_to_bson('', item, False)
            except errors.InvalidDocument:
                l[index] = str(item)
    return l

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
        if hasattr(request, 'user'):
            authenticated = bool(request.user.is_authenticated())
        else:
            authenticated = False
        doc = {
            'time': datetime.datetime.utcnow(),
            'timestamp': timestamp,
            'total': total,
            'status_code': response.status_code,
            'headers': dict(response._headers.values()),
            'encoding': request.encoding or settings.DEFAULT_CHARSET,
            'method': request.method,
            'cached?': bool(self.request_was_cached(request)),
            'authenticated?': authenticated,
            'secure?': request.is_secure(),
            'ajax?': request.is_ajax(),
            'host': request.get_host(),
            'path': request.path,
            'GET': _fix_dict(request.GET),
            'POST': _fix_dict(request.POST),
            'META': _fix_dict(request.META),
            'raw_post_data': pymongo.binary.Binary(request.raw_post_data),
            'view_func': getattr(request, 'view_func', ''),
            'view_args': _fix_values(getattr(request, 'view_args', [])),
            'view_kwargs': _fix_dict(getattr(request, 'view_kwargs', {}))
            }
        self.collection.insert(doc)
        return response
