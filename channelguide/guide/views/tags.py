from sqlalchemy import desc

from channelguide import util, cache
from channelguide.guide.models import Tag
from channelguide.guide.templateutil import Pager, make_two_column_list

@cache.aggresively_cache
def index(request):
    q = request.db_session.query(Tag)
    select = q.select(order_by=desc(Tag.c.channel_count))
    pager =  Pager(45, select, request)
    return util.render_to_response(request, 'tag-list.html', {
        'pager': pager,
    })

@cache.aggresively_cache
def tag(request, id):
    return make_two_column_list(request, id, Tag, _('Tag: %s'),
            join_path=['tags'])
