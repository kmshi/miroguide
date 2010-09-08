from django.conf import settings
from django.core.urlresolvers import resolve, Resolver404
from django.views.decorators.cache import never_cache
from django.http import HttpResponse
from django.shortcuts import get_object_or_404

from channelguide import util

from channelguide.channels.models import Channel
from channelguide.channels.views import channel as channel_view
from channelguide.guide.views.firsttime import index as firsttime_index
from channelguide.subscriptions.models import Subscription

@never_cache
def subscribe_hit(request, id):
    """Used by our ajax call handleSubscriptionLink.  It will get a security
    error if we redirect it to a URL outside the channelguide, so we don't do
    that
    """
    ids = [id] + [int(k) for k in request.GET]
    for id in ids:
        channel = get_object_or_404(Channel, pk=id)
        referer = request.META.get('HTTP_REFERER', '')
        ignore_for_recommendations = False
        if referer.startswith(settings.BASE_URL_FULL):
            referer = util.chop_prefix(referer, settings.BASE_URL_FULL)
            if not referer.startswith("/"):
                referer = '/' + referer # make sure it starts with a slash
            try:
                resolved = resolve(referer)
            except Resolver404:
                pass
            else:
                if resolved is not None:
                    func, args, kwargs = resolved
                    if func == channel_view and args[0] != id:
                        ignore_for_recommendations = True
                    elif func == firsttime_index:
                        ignore_for_recommendations = True
        ip = request.META.get('REMOTE_ADDR', '0.0.0.0')
        if ip == '127.0.0.1':
            ip = request.META.get('HTTP_X_FORWARDED_FOR', '0.0.0.0')
        Subscription.objects.add(
            channel, ip,
            ignore_for_recommendations=ignore_for_recommendations)

    return HttpResponse("Hit successfull")
