from django.conf import settings
from channelguide import util

style_nonce = util.random_string(5)

def guide(request):
    """Channelguide context processor.  These attributes get added to every
    template context.
    """

    return {
            'BASE_URL': settings.BASE_URL,
            'STATIC_BASE_URL': settings.STATIC_BASE_URL,
            'GUIDE_EMAIL': settings.EMAIL_FROM,
            'style_nonce': style_nonce,
            'request': request,
            'user': request.user,
            'total_channels': request.total_channels,
        }
