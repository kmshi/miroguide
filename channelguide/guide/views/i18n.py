# Copyright (c) 2009 Participatory Culture Foundation
# See LICENSE for details.

from django.views.i18n import set_language as django_set_language

START = '<span class="code">'
END = '</span>'

def set_language(request):
    if request.method == 'POST':
        if request.POST.get('language'):
            language = request.POST['language'].lower()
            if language.startswith('<'):
                # Internet Explorer sends the contents of the <button> tag
                # instead of its value
                startPos = language.find(START) + len(START) - 1
                endPos = language.find(END, startPos)
                language = language[startPos:endPos]
                request.POST = request.POST.copy()
                request.POST['language'] = language
    return django_set_language(request)
