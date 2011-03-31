# Copyright (c) 2009 Participatory Culture Foundation
# See LICENSE for details.

import urlparse
import re

from django.conf import settings
from django.http import Http404
from django.core.paginator import Paginator, InvalidPage
from django.shortcuts import get_object_or_404, render_to_response
from django.template.context import RequestContext

from channelguide import util
from channelguide.channels.models import Item

def item(request, id):
    item = get_object_or_404(Item.objects.select_related(), pk=id)
    if item.date is None:
        previousSet = Item.objects.filter(channel=item.channel,
                                          pk__lt=item.pk).order_by('-pk')
        nextSet = Item.objects.filter(channel=item.channel,
                                      pk__gt=item.pk).order_by('pk')
    else:
        previousSet = Item.objects.filter(channel=item.channel,
                                          date__lt=item.date).order_by('-date')
        nextSet = Item.objects.filter(channel=item.channel,
                                      date__gt=item.date).order_by('date')

    try:
        previous = previousSet[0]
    except Item.DoesNotExist:
        previous = None

    index = nextSet.count()

    if index:
        next = nextSet[0]
    else:
        next = None

    default_page = (index // 10) + 1
    paginator = Paginator(item.channel.items.all(), 10)
    try:
        page = paginator.page(request.GET.get('page', default_page))
    except InvalidPage:
        raise Http404
    for i in page.object_list:
        i.channel = item.channel

    share_url = urlparse.urljoin(
        settings.BASE_URL_FULL,
        '/items/%s' % id)
    share_links = util.get_share_links(share_url, item.name)

    context = {'item': item,
               'channel': item.channel,
               'audio': item.channel.state == item.channel.AUDIO,
               'bittorrent': item.mime_type == 'application/x-bittorrent',
               'previous': previous,
               'next': next,
               'page': page,
               'share_url': share_url,
               'hide_share': request.GET.get('share') != 'true',
               'share_type': 'item',
               'share_links': share_links,
               'feed_url': item.channel.url,
               'item_name': item.name,
               'file_url': item.url
               }

    if share_url:
        context['google_analytics_ua'] = None

    return render_to_response('channels/playback.html', context,
                              context_instance=RequestContext(request))
