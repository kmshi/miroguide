from sqlalchemy import desc

from channelguide import util, cache
from channelguide.guide.models import Category
from channelguide.guide.templateutil import make_two_column_list

@cache.aggresively_cache
def index(request):
    q = request.db_session.query(Category)
    select = q.select(order_by=desc(Category.c.channel_count))
    return util.render_to_response(request, 'group-list.html', {
        'group_name': _('Categories'),
        'groups': select,
    })

@cache.aggresively_cache
def category(request, id):
    return make_two_column_list(request, id, Category, _('Category: %s'), 
            join_path=['categories'])
