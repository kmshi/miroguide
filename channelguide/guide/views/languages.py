from copy import copy

from django.conf import settings
from sqlalchemy import exists, func, select

from channelguide import util, cache
from channelguide.guide import tables, templateutil 
from channelguide.guide.auth import admin_required
from channelguide.guide.models import Language, Channel
from channelguide.guide.models.mappings import channel_select

@cache.aggresively_cache
def index(request):
    q = request.db_session.query(Language)
    return util.render_to_response(request, 'group-list.html', {
        'group_name': _('Channels by Language'),
        'groups': q.select(order_by=Language.c.name),
    })

def add_language_whereclause(select, language):
    select.append_whereclause(tables.language.c.id == language.id)
    join_primary = (tables.channel.c.primary_language_id==tables.language.c.id)
    join_secondary = exists(['*'], 
        (tables.channel.c.id==tables.secondary_language_map.c.channel_id) &
        (tables.language.c.id==tables.secondary_language_map.c.language_id))
    select.append_whereclause(join_primary | join_secondary)

def count_channels_by_language(language):
    rv = select([func.count('*')], from_obj=[tables.channel])
    add_language_whereclause(rv, language)
    return rv

def select_channels_by_language(language):
    select = copy(channel_select)
    add_language_whereclause(select, language)
    return select

def make_channels_pager(request, language):
    count_select = count_channels_by_language(language)
    count = request.connection.execute(count_select).scalar()
    select = select_channels_by_language(language)
    select.order_by(templateutil.get_order_by_from_request(request, select.c))
    query = request.db_session.query(Channel)
    def callback(offset, limit):
        select.offset = offset
        select.limit = limit
        return query.instances(request.connection.execute(select))
    return templateutil.ManualPager(8, count, callback, request)

@cache.aggresively_cache
def view(request, id):
    language = util.get_object_or_404(request.db_session.query(Language), id)
    pager = make_channels_pager(request, language)
    return util.render_to_response(request, 'two-column-list.html', {
        'header': _("Language: %s") % language.name,
        'pager': pager,
        'order_select': templateutil.OrderBySelect(request, 
            language.get_absolute_url()),
    })

@admin_required
def moderate(request):
    query = request.db_session.query(Language, order_by='name')
    return util.render_to_response(request, 'edit-categories.html', {
        'header': _('Edit Languages'),
        'action_url_prefix': settings.BASE_URL + "languages",
        'categories': query.select().list(),
    })

@admin_required
def add(request):
    if request.method == 'POST':
        new_lang = Language(request.POST['name'])
        request.db_session.save(new_lang)
    return util.redirect('languages/moderate')

@admin_required
def delete(request):
    if request.method == 'POST':
        lang = request.db_session.get(Language, request.POST['id'])
        request.db_session.delete(lang)
    return util.redirect('languages/moderate')

@admin_required
def change_name(request):
    if request.method == 'POST':
        lang = request.db_session.get(Language, request.POST['id'])
        lang.name = request.POST['name']
        request.db_session.update(lang)
    return util.redirect('languages/moderate')
