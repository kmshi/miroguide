# Copyright (c) 2008-2009 Participatory Culture Foundation
# See LICENSE for details.

from django.conf import settings
from django.utils.translation import gettext as _

from channelguide import util, cache
from channelguide.guide.auth import admin_required
from channelguide.guide.models import Category

@cache.aggresively_cache
def index(request):
    query = Category.query().load('channel_count')
    query.order_by('channel_count', desc=True)
    query.cacheable = cache.client
    query.cacheable_time = 3600
    rows = list(query.execute(request.connection))
    return util.render_to_response(request, 'group-list.html', {
        'group_name': _('Genres'),
        'groups': rows,
    })

@admin_required
def moderate(request):
    categories = Category.query().order_by('name').execute(request.connection)
    return util.render_to_response(request, 'edit-categories.html', {
        'header': _('Edit Genre'),
        'new_label': _('New Genre'),
        'action_url_prefix': settings.BASE_URL + "genres",
        'categories': categories,
    })

@admin_required
def add(request):
    if request.method == 'POST':
        new_category = Category(request.POST['name'])
        new_category.save(request.connection)
    return util.redirect('genres/moderate')

@admin_required
def delete(request):
    if request.method == 'POST':
        category = Category.get(request.connection, request.POST['id'])
        category.delete(request.connection)
    return util.redirect('genres/moderate')

@admin_required
def change_name(request):
    if request.method == 'POST' and request.POST.get('name'):
        category = Category.get(request.connection, request.POST['id'])
        category.name = request.POST['name']
        category.save(request.connection)
    return util.redirect('genres/moderate')

@admin_required
def toggle_frontpage(request):
    if request.method == 'POST':
        category = Category.get(request.connection, request.POST['id'])
        category.on_frontpage = not category.on_frontpage
        category.save(request.connection)
    return util.redirect('genres/moderate')
