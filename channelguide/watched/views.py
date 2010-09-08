# Copyright (c) 2009 Participatory Culture Foundation
# See LICENSE for details.

from channelguide.watched.models import WatchedVideos
from channelguide.channels.models import Channel, Item
from django.http import HttpResponse

def watched(request):
    WatchedVideos.objects.increment()
    feedURL = request.REQUEST.get('feed', '')
    itemURL = request.REQUEST.get('item', '')
    try:
        item = Item.objects.get(url=itemURL)
    except Item.DoesNotExist:
        item = None
    else:
        channel = item.channel
    if item is None:
        try:
            channel = Channel.objects.get(url=feedURL)
        except Channel.DoesNotExist:
            channel = None
    if channel:
        WatchedVideos.objects.increment(channel)
    if item:
        WatchedVideos.objects.increment(item)
    return HttpResponse('Watched video ping successful.')
