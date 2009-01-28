# Copyright (c) 2008 Participatory Culture Foundation
# See LICENSE for details.

from django.conf import settings
from django.core.paginator import Paginator
from django.http import Http404

from channelguide import util, cache
from channelguide.guide.auth import moderator_required, login_required
from channelguide.guide.models import Channel, ChannelNote, ModeratorPost
from channelguide.guide.templateutil import QueryObjectList

@login_required
def add_note(request):
    try:
        channel_id = int(request.POST['channel-id'])
    except (ValueError, KeyError):
        raise Http404
    query = Channel.query().join('notes', 'owner')
    channel = util.get_object_or_404(request.connection, query, channel_id)
    note = ChannelNote.create_note_from_request(request)
    request.user.check_can_edit(channel)
    channel.add_note(request.connection, note)
    if request.user.id != channel.owner_id:
        note.send_email(request.connection)
    return util.redirect('channels/%d' % channel.id)

@moderator_required
def moderator_board(request):
    query = ModeratorPost.query().order_by('created_at', desc=True)
    query.join('user')
    paginator = Paginator(QueryObjectList(request.connection, query), 5)
    page = paginator.page(request.GET.get('page', 1))
    return util.render_to_response(request, 'moderator-board.html', {
        'page': page,
        })

@moderator_required
def add_moderator_post(request):
    post = ModeratorPost.create_note_from_request(request)
    send_checked = (request.POST.get('send-email') and 
            request.user.is_supermoderator())
    post.send_email(request.connection, send_checked)
    post.save(request.connection)
    return util.redirect('notes/moderator-board')

@moderator_required
def post(request, id):
    post = util.get_object_or_404(request.connection, ModeratorPost, id)
    if request.method == 'POST':
        if request.POST['action'] == 'delete':
            request.user.check_is_supermoderator()
            post.delete(request.connection)
            return util.redirect_to_referrer(request)
    return util.redirect('notes/moderator-board')
