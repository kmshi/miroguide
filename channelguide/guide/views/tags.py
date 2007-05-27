from channelguide import util, cache
from channelguide.guide import templateutil
from channelguide.guide.models import Tag, Channel

@cache.aggresively_cache
def index(request):
    query = Tag.query().load('channel_count')
    query.order_by('channel_count', desc=True)
    pager =  templateutil.Pager(45, query, request)
    return util.render_to_response(request, 'tag-list.html', {
        'pager': pager,
    })

@cache.aggresively_cache
def tag(request, id):
    tag = Tag.get(request.connection, id)
    query = Channel.query_approved().join('tags')
    query.joins['tags'].where(id=id)
    templateutil.order_channels_using_request(query, request)
    pager =  templateutil.Pager(8, query, request)
    return util.render_to_response(request, 'two-column-list.html', {
        'header': tag,
        'pager': pager,
        'order_select': templateutil.OrderBySelect(request),
    })
