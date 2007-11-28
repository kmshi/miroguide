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

@cache.aggresively_cache(adult_differs=True)
def tag(request, id):
    tag = util.get_object_or_404(request.connection, Tag, id)
    sort = templateutil.getchannels_sort_using_request(request)
    pager =  templateutil.GetChannelsPager(8, request, filter="tag",
            filter_value=tag.id, sort=sort)
    return util.render_to_response(request, 'two-column-list.html', {
        'header': tag.name,
        'pager': pager,
        'order_select': templateutil.OrderBySelect(request),
    })
