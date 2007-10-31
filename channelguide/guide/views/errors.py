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
    path = settings.BASE_URL_FULL[:-1] + request.get_full_path()
    title = 'Error %s on %s' % (id, path)
    io = cStringIO.StringIO()
    io.write('URL: %s\n\n' % path)
    traceback.print_exc(None, io)
    io.write('\nRequest Object:\n')
    pprint.pprint(request, stream=io)
    if request.user.is_authenticated():
        io.write('\nUser Name: %s' % request.user.username)
        io.write('\nE-mail: %s' % request.user.email)
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
