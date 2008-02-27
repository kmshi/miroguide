# Copyright (c) 2008 Participatory Culture Foundation
# See LICENSE for details.

from django.conf import settings
from channelguide import util
import sha, os

style_file = os.path.dirname(__file__) + '/../static/css/style.css'
style_nonce = hash(os.stat(style_file))

def guide(request):
    """Channelguide context processor.  These attributes get added to every
    template context.
    """

    return {
            'BASE_URL': settings.BASE_URL,
            'STATIC_BASE_URL': settings.STATIC_BASE_URL,
            'GUIDE_EMAIL': settings.EMAIL_FROM,
            'google_analytics_ua': settings.GOOGLE_ANALYTICS_UA,
            'style_nonce': style_nonce,
            'request': request,
            'user': request.user,
            'total_channels': request.total_channels,
        }
