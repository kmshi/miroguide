# Copyright (c) 2008-2009 Participatory Culture Foundation
# See LICENSE for details.

from django.conf import settings
from django.utils.translation import gettext as _

from channelguide import util, cache
from channelguide.guide.auth import admin_required
from channelguide.guide.models import Language

@cache.aggresively_cache
def index(request):
    audio = request.path.startswith('/audio')
    if audio:
        query = Language.query().load('audio_count').order_by('name')
    else:
        query = Language.query().load('channel_count').order_by('name')
    query.cacheable = cache.client
    query.cacheable_time = 3600
    return util.render_to_response(request, 'group-list.html', {
        'group_name': _('Shows by Language'),
        'groups': query.execute(request.connection),
        'audio': audio
    })

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
    if request.method == 'POST' and request.POST.get('name'):
        language = Language.get(request.connection, request.POST['id'])
        language.name = request.POST['name']
        language.save(request.connection)
    return util.redirect('languages/moderate')
