from copy import copy

from django.conf import settings
from sqlhelper import sql

from channelguide import util, cache
from channelguide.guide import tables, templateutil 
from channelguide.guide.auth import admin_required
from channelguide.guide.models import Language, Channel

@cache.aggresively_cache
def index(request):
    query = Language.query().load('channel_count').order_by('name')
    query.cacheable = cache.client
    query.cacheable_time = 3600
    return util.render_to_response(request, 'group-list.html', {
        'group_name': _('Channels by Language'),
        'groups': query.execute(request.connection),
    })

def secondary_language_exists_where(language_id):
    select = sql.Select('*')
    select.froms.append('cg_secondary_language_map')
    select.wheres.append('channel_id=cg_channel.id')
    select.wheres.append('language_id=%s', language_id)
    return select.exists()

def view(request, id):
    language = Language.get(request.connection, id)
    order_select = templateutil.OrderBySelect(request)
    query = Channel.query_approved(user=request.user)
    query.where((Channel.c.primary_language_id==id) |
            secondary_language_exists_where(id))
    return templateutil.render_limited_query(request, query,
         _("Language: %s") % language.name)

@admin_required
def moderate(request):
    query = Language.query().order_by('name')
    return util.render_to_response(request, 'edit-categories.html', {
        'header': _('Edit Languages'),
        'new_label': _('New Language'),
        'action_url_prefix': settings.BASE_URL + "languages",
        'categories': query.execute(request.connection),
    })

@admin_required
def add(request):
    if request.method == 'POST':
        new_language = Language(request.POST['name'])
        new_language.save(request.connection)
    return util.redirect('languages/moderate')

@admin_required
def delete(request):
    if request.method == 'POST':
        language = Language.get(request.connection, request.POST['id'])
        language.delete(request.connection)
    return util.redirect('languages/moderate')

@admin_required
def change_name(request):
    if request.method == 'POST':
        language = Language.get(request.connection, request.POST['id'])
        language.name = request.POST['name']
        language.save(request.connection)
    return util.redirect('languages/moderate')
