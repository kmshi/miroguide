# Copyright (c) 2008 Participatory Culture Foundation
# See LICENSE for details.

import math

from django.conf import settings

from channelguide.labels.models import Language, Category
from channelguide.user_profile.models import UserProfile
from channelguide.user_profile.forms import LoginForm, RegisterForm

def guide(request):
    """Channelguide context processor.  These attributes get added to every
    template context.
    """
    categories = Category.objects.order_by('name')
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
        'settings': settings,
        'language_options': False,
        'categories_list': categories,
        'categories_loop': categories_loop,
        }
    context['login'] = LoginForm()
    context['register'] = RegisterForm()

    if not request.user.is_authenticated():
        context['language_options'] = True
    else:
        try:
            profile = request.user.get_profile()
        except UserProfile.DoesNotExist:
            pass # happens during the test cases, if the user is loaded via
                 # fixture
        else:

            context['profile'] = profile

            # figure out whether to show language options
            if 'django_language' in request.session:
                if request.session['django_language'] != profile.language:
                    profile.language = request.session['django_language']
                    profile.save()
            if profile.language:
                if 'django_language' not in request.session:
                    request.session['django_language'] = profile.language
                languageName = settings.ENGLISH_LANGUAGE_MAP.get(
                    profile.language)
                if languageName:
                    try:
                        dbLanguage = Language.objects.get(name=languageName)
                    except Language.DoesNotExist:
                        pass
                    else:
                        if not profile.filter_languages:
                            context['language_options'] = True
                        else:
                            if profile.shown_languages.count() == 1 and \
                                    profile.shown_languages.all()[0] == \
                                    dbLanguage:
                                context['language_options'] = True
    return context
