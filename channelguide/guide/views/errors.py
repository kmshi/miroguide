# Copyright (c) 2008-2009 Participatory Culture Foundation
# See LICENSE for details.

import logging
import random
import sys
import traceback
import MySQLdb

from django import http
from django.conf import settings
from django.template import Context, loader

def error_500(request):
    return http.HttpResponseServerError(render_error_500(request))

def render_error_500(request):
    id = '%d-%d' % (random.randint(100, 999), random.randint(1000, 9999))
    context = Context({
        'BASE_URL': settings.BASE_URL,
        'STATIC_BASE_URL': settings.STATIC_BASE_URL,
        'id': id,
        'user': None,
    })
    exc_type = sys.exc_info()[0]
    if exc_type in (MySQLdb.MySQLError,): # database error
        context['database_error'] = True
    template = loader.get_template('500.html')
    logging.error("Exception %s: %s", id, traceback.format_exc())
    return template.render(context)
