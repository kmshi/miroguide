# Copyright (c) 2008-2009 Participatory Culture Foundation
# See LICENSE for details.

from django.contrib.auth.decorators import login_required
from django.http import Http404, HttpResponseRedirect
from django.shortcuts import get_object_or_404

from channelguide.channels.models import Channel
from channelguide.ratings.models import Rating

@login_required
def rate(request, id):
    channel = get_object_or_404(Channel, pk=id)
    score = request.REQUEST.get('rating')
    if score not in ['0', '1', '2', '3', '4', '5']:
        raise Http404
    rating, created = Rating.objects.get_or_create(channel=channel,
                                                   user=request.user)
    if score == '0':
        rating.rating = None
    else:
        rating.rating = int(score)
    rating.save()
    if request.GET.get('referrer'):
        redirect = request.GET['referer']
    else:
        redirect = channel.get_absolute_url()
    return HttpResponseRedirect(redirect)
