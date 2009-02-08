
# Copyright (c) 2008-9 Participatory Culture Foundation
# See LICENSE for details.

from django.core.paginator import Paginator, InvalidPage
from django.http import Http404
from channelguide import util, cache
from channelguide.guide import templateutil
from channelguide.guide.models import Tag

@cache.aggresively_cache
def index(request):
    query = Tag.query().load('channel_count')
    query.order_by('channel_count', desc=True)
    query.cacheable = cache.client
    query.cacheable_time = 3600
    paginator = Paginator(templateutil.QueryObjectList(request.connection,
                                                       query), 45)
    try:
        page = paginator.page(request.GET.get('page', 1))
    except InvalidPage:
        raise Http404
    return util.render_to_response(request, 'tag-list.html', {
        'page': page,
    })
