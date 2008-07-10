# Copyright (c) 2008 Participatory Culture Foundation
# See LICENSE for details.

from channelguide import util, cache
from channelguide.guide import templateutil
from channelguide.guide.models import Tag, Channel

@cache.aggresively_cache
def index(request):
    query = Tag.query().load('channel_count')
    query.order_by('channel_count', desc=True)
    query.cacheable = cache.client
    query.cacheable_time = 3600
    pager =  templateutil.Pager(45, query, request)
    return util.render_to_response(request, 'tag-list.html', {
        'pager': pager,
    })
