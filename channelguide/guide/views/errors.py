import logging
import random
import traceback
import pprint
import cStringIO

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
    title = 'Error %s on %s' % (id, request.get_full_path())
    print title
    io = cStringIO.StringIO()
    traceback.print_exc(None, io)
    io.write('\nRequest Object:\n')
    pprint.pprint(request, stream=io)
    if request.user.is_authenticated():
        io.write('\nUser Name: %s\n' % request.user.name)
        io.write('\nE-mail: %s' % request.user.email)
    else:
        io.write('\nAnonymous User')
    body = io.getvalue()
    emails = ["%s <%s>" % admin for admin in settings.ADMINS]
    util.send_email(title, body, emails, break_lines=False)
    template = loader.get_template('500.html')
    logging.error("Exception %s: %s", id, traceback.format_exc())
    return template.render(context)
