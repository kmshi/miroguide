from sqlalchemy import desc

from channelguide import util
from channelguide.guide.models import Category
from channelguide.guide.templateutil import make_two_column_list

def index(request):
    q = request.db_session.query(Category)
    select = q.select(order_by=desc(Category.c.channel_count))
    return util.render_to_response(request, 'group-list.html', {
        'group_name': _('Categories'),
        'groups': select,
    })

def category(request, id):
    return make_two_column_list(request, id, Category, _('Category: %s'), 
            join_path=['categories'])

