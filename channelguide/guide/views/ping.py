from channelguide.guide.models import WatchedVideos, Channel, Item
from django.http import HttpResponse

def watched(request):
    WatchedVideos.increment(request.connection)
    feedURL = request.REQUEST.get('feed', '')
    itemURL = request.REQUEST.get('item', '')
    try:
        item = Item.query(url=itemURL).get(request.connection)
    except LookupError:
        item = None
    try:
        channel = Channel.query(url=feedURL).get(request.connection)
    except LookupError:
        channel = None
    if channel is None and item is not None:
        item.join('channel').execute(request.connection)
        channel = item.channel
    if channel:
        WatchedVideos.increment(request.connection, channel)
    if item:
        WatchedVideos.increment(request.connection, item)
    return HttpResponse('Watched video ping successful.')
