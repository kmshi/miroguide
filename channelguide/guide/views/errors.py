from django import http
from django.conf import settings
from django.template import Context, RequestContext, loader

def error_500(request):
    return http.HttpResponseServerError(render_error_500())

def render_error_500():
    context = Context({
        'BASE_URL': settings.BASE_URL,
        'STATIC_BASE_URL': settings.STATIC_BASE_URL,
    })
    template = loader.get_template('500.html')
    return template.render(context)
