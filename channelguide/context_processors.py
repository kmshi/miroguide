# Copyright (c) 2008 Participatory Culture Foundation
# See LICENSE for details.

import math

from django.conf import settings

from channelguide.guide.forms import LoginForm, RegisterForm
from channelguide.guide.models import Language, Category

def guide(request):
    """Channelguide context processor.  These attributes get added to every
    template context.
    """
    categories = Category.query().order_by('name').execute(request.connection)
    category_column_length = math.ceil(len(categories) / 4.0)
    categories_loop = ['%i:%i' % (i*category_column_length, (i + 1) *
                                  category_column_length) for i in range(4)]
    context = {
        'DEBUG': settings.DEBUG,
        'BASE_URL': settings.BASE_URL,
        'BASE_URL_FULL': settings.BASE_URL_FULL,
        'STATIC_BASE_URL': settings.STATIC_BASE_URL,
        'GUIDE_EMAIL': settings.EMAIL_FROM,
        'LANGUAGES': settings.LANGUAGES,
        'google_analytics_ua': settings.GOOGLE_ANALYTICS_UA,
        'request': request,
        'user': request.user,
        'language_options': False,
        'categories_list': categories,
        'categories_loop': categories_loop,
        }
    if not request.user.is_authenticated():
        context['login'] = LoginForm(request)
        context['register'] = RegisterForm(request)
        context['language_options'] = True
    else:
        # figure out language options
        if hasattr(request, 'connection') and request.user.language:
            languageName = settings.ENGLISH_LANGUAGE_MAP.get(request.user.language)
            if languageName:
                dbLanguages = Language.query(name=languageName).execute(request.connection)
                if dbLanguages:
                    if not request.user.filter_languages:
                        context['language_options'] = True
                    else:
                        request.user.join('shown_languages').execute(request.connection)
                        if len(request.user.shown_languages) == 1 and \
                                request.user.shown_languages[0].id == dbLanguages[0].id:
                            context['language_options'] = True
    return context
