from django.conf import settings

from channelguide import util, cache
from channelguide.guide import templateutil
from channelguide.guide.auth import admin_required
from channelguide.guide.models import Category, Channel

@cache.aggresively_cache
def index(request):
    query = Category.query().load('channel_count')
    query.order_by('channel_count', desc=True)
    query.cacheable = cache.client
    query.cacheable_time = 3600
    return util.render_to_response(request, 'group-list.html', {
        'group_name': _('Categories'),
        'groups': query.execute(request.connection),
    })

@cache.aggresively_cache
def category(request, name):
    category = util.get_object_or_404_by_name(request.connection, Category,
            name)
    query = Channel.query_approved().join('categories')
    query.joins['categories'].where(id=category.id)
    templateutil.order_channels_using_request(query, request)
    pager =  templateutil.Pager(8, query, request)
    return util.render_to_response(request, 'two-column-list.html', {
        'header': category.name,
        'pager': pager,
        'order_select': templateutil.OrderBySelect(request),
    })

@admin_required
def moderate(request):
    categories = Category.query().order_by('name').execute(request.connection)
    return util.render_to_response(request, 'edit-categories.html', {
        'header': _('Edit Categories'),
        'new_label': _('New Category'),
        'action_url_prefix': settings.BASE_URL + "categories",
        'categories': categories,
    })

@admin_required
def add(request):
    if request.method == 'POST':
        new_category = Category(request.POST['name'])
        new_category.save(request.connection)
    return util.redirect('categories/moderate')
@admin_required
def delete(request):
    if request.method == 'POST':
        category = Category.get(request.connection, request.POST['id'])
        category.delete(request.connection)
    return util.redirect('categories/moderate')

@admin_required
def change_name(request):
    if request.method == 'POST':
        category = Category.get(request.connection, request.POST['id'])
        category.name = request.POST['name']
        category.save(request.connection)
    return util.redirect('categories/moderate')
