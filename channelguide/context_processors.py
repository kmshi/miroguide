# Copyright (c) 2008 Participatory Culture Foundation
# See LICENSE for details.

from django.conf import settings
from channelguide.guide.forms import LoginForm, RegisterForm

def guide(request):
    """Channelguide context processor.  These attributes get added to every
    template context.
    """

    context = {
        'DEBUG': settings.DEBUG,
        'BASE_URL': settings.BASE_URL,
        'STATIC_BASE_URL': settings.STATIC_BASE_URL,
        'GUIDE_EMAIL': settings.EMAIL_FROM,
        'google_analytics_ua': settings.GOOGLE_ANALYTICS_UA,
        'request': request,
        'user': request.user,
        }
    if not request.user.is_authenticated():
        context['login'] = LoginForm(request)
        context['register'] = RegisterForm(request)
    return context
