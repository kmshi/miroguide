from django import http
from django.conf import settings
from django.utils.translation import check_for_language, activate, to_locale, get_language

def set_language(request):
    """
    Based off django.views.i18n.set_language.
    """
    lang_code = request.GET.get('language', None)
    next = request.GET.get('next', None)
    if not next:
        next = request.META.get('HTTP_REFERER', None)
    if not next:
        next = '/'
    response = http.HttpResponseRedirect(next)
    if lang_code and check_for_language(lang_code):
        if lang_code != settings.LANGUAGE_CODE:
            response.set_cookie('django_language', lang_code)
            if hasattr(request, 'session'):
                request.session['django_language'] = lang_code
        else:
            response.delete_cookie('django_language')
            if hasattr(request, 'session') and 'django_language' in request.session:
                del request.session['django_language']
    return response
