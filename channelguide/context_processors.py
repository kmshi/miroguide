from django.conf import settings

def guide(request):
    """Channelguide context processor.  These attributes get added to every
    template context.
    """

    return {
            'BASE_URL': settings.BASE_URL,
            'GUIDE_EMAIL': settings.EMAIL_FROM,
            'request': request,
            'user': request.user,
        }

