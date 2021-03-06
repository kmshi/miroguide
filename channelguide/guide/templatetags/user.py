# Copyright (c) 2008 Participatory Culture Foundation
# See LICENSE for details.

from django.conf import settings
from django.template import Library
register = Library()

@register.inclusion_tag('guide/user.html', takes_context=True)
def show_user(context, user_to_view):
    return {'user': user_to_view, 'perms': context['perms'],
            'BASE_URL': settings.BASE_URL}
