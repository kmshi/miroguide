import logging
import random
import traceback

from django import http
from django.conf import settings
from django.template import Context, RequestContext, loader

def error_500(request):
    return http.HttpResponseServerError(render_error_500())

def render_error_500():
    id = '%d-%d' % (random.randint(100, 999), random.randint(1000, 9999))
    context = Context({
        'BASE_URL': settings.BASE_URL,
        'STATIC_BASE_URL': settings.STATIC_BASE_URL,
        'id': id,
        'user': None,
    })
    template = loader.get_template('500.html')
    logging.error("Exception %s: %s", id, traceback.format_exc())
    return template.render(context)
