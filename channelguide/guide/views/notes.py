from django.conf import settings
from django.http import Http404
from sqlalchemy import desc

from channelguide import util
from channelguide.guide.auth import moderator_required, login_required
from channelguide.guide.models import Channel, ChannelNote, ModeratorPost
from channelguide.guide.templateutil import Pager

@login_required
def add_note(request):
    try:
        channel_id = int(request.POST['channel-id'])
    except ValueError:
        raise Http404
    query = request.db_session.query(Channel)
    channel = util.get_object_or_404(query, channel_id)
    request.user.check_can_edit(channel)
    note = ChannelNote.create_note_from_request(request)
    channel.notes.append(note)
    if request.POST.get('send-email') and request.user.is_moderator():
        note.send_email()
    return util.redirect('channels/%d#notes' % channel.id)

@moderator_required
def note(request, id):
    query = request.db_session.query(ChannelNote)
    note = util.get_object_or_404(query, id)
    channel = note.channel
    if request.method == 'POST':
        if request.POST['action'] == 'delete':
            request.db_session.delete(note)
            return util.redirect_to_referrer(request)
    return util.redirect('channels/%d#notes' % channel.id)

@moderator_required
def moderator_board(request):
    query = request.db_session.query(ModeratorPost)
    posts = query.select(order_by=desc(ModeratorPost.c.created_at))
    pager =  Pager(5, posts, request)

    return util.render_to_response(request, 'moderator-board.html', {
        'posts': pager.items,
        'pager': pager,
        })

@moderator_required
def add_moderator_post(request):
    post = ModeratorPost.create_note_from_request(request)
    if request.POST.get('send-email') and request.user.is_supermoderator():
        post.send_email()
    return util.redirect('notes/moderator-board')

@moderator_required
def post(request, id):
    query = request.db_session.query(ModeratorPost)
    post = util.get_object_or_404(query, id)
    if request.method == 'POST':
        if request.POST['action'] == 'delete':
            request.user.check_is_supermoderator()
            request.db_session.delete(post)
            return util.redirect_to_referrer(request)
    return util.redirect('notes/moderator-board')
