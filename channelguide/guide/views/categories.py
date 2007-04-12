from django.conf import settings
from sqlalchemy import desc

from channelguide import util, cache
from channelguide.guide.auth import admin_required
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

@admin_required
def moderate(request):
    query = request.db_session.query(Category, order_by='name')
    return util.render_to_response(request, 'edit-categories.html', {
        'header': _('Edit Categories'),
        'action_url_prefix': settings.BASE_URL + "categories",
        'categories': query.select().list(),
    })

@admin_required
def add(request):
    if request.method == 'POST':
        new_category = Category(request.POST['name'])
        request.db_session.save(new_category)
    return util.redirect('categories/moderate')

@admin_required
def delete(request):
    if request.method == 'POST':
        category = request.db_session.get(Category, request.POST['id'])
        request.db_session.delete(category)
    return util.redirect('categories/moderate')

@admin_required
def change_name(request):
    if request.method == 'POST':
        category = request.db_session.get(Category, request.POST['id'])
        category.name = request.POST['name']
        request.db_session.update(category)
    return util.redirect('categories/moderate')
