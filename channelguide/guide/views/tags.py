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

def tag(request, id):
    tag = util.get_object_or_404(request.connection, Tag, id)
    query = Channel.query_approved(user=request.user).join('tags')
    query.joins['tags'].where(id=id)
    return templateutil.render_limited_query(request, query, tag.name)
