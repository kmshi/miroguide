# Copyright (c) 2008 Participatory Culture Foundation
# See LICENSE for details.

import logging
import random
import sys
import traceback
import pprint
import cStringIO
import MySQLdb

from django import http
from django.conf import settings
from django.template import Context, RequestContext, loader
from channelguide import util

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
    if not hasattr(request, 'get_full_path'):
        path = ' Path Unknown'
    else:
        path = request.get_full_path()
    path = settings.BASE_URL_FULL[:-1] + path
    title = 'Error %s on %s' % (id, path)
    io = cStringIO.StringIO()
    io.write('URL: %s\n\n' % path)
    traceback.print_exc(None, io)
    io.write('\nRequest Object:\n')
    pprint.pprint(request, stream=io)
    if hasattr(request, 'user') and request.user.is_authenticated():
        io.write('\nUser Name: %s' % request.user.username.encode('utf8'))
        io.write('\nE-mail: %s' % request.user.email.encode('utf8'))
        email_from = request.user.email
    else:
        io.write('\nAnonymous User')
        email_from = None
    body = io.getvalue()
    emails = [admin[1] for admin in settings.ADMINS]
    util.send_mail(title, body, emails, email_from=email_from,
            break_lines=False)
    template = loader.get_template('500.html')
    logging.error("Exception %s: %s", id, traceback.format_exc())
    return template.render(context)
