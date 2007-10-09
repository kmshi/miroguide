from django.conf import settings
from django.http import Http404

from channelguide import util, cache
from channelguide.guide.auth import moderator_required, login_required
from channelguide.guide.models import Channel, ChannelNote, ModeratorPost
from channelguide.guide.templateutil import Pager

@login_required
def add_note(request):
    try:
        channel_id = int(request.POST['channel-id'])
    except ValueError:
        raise Http404
    query = Channel.query().join('notes', 'owner')
    channel = util.get_object_or_404(request.connection, query, channel_id)
    note = ChannelNote.create_note_from_request(request)
    if note.type == ChannelNote.MODERATOR_ONLY:
        request.user.check_is_moderator()
    else:
        request.user.check_can_edit(channel)
    channel.add_note(request.connection, note)
    if request.POST.get('send-email') and request.user.is_moderator():
        note.send_email(request.connection)
    return util.redirect('channels/%d#notes' % channel.id)

@moderator_required
def note(request, id):
    note = util.get_object_or_404(request.connection, ChannelNote, id)
    if request.method == 'POST':
        if request.POST['action'] == 'delete':
            note.delete(request.connection)
            return util.redirect_to_referrer(request)
    return util.redirect('channels/%d#notes' % note.channel_id)

@moderator_required
def moderator_board(request):
    query = ModeratorPost.query().order_by('created_at', desc=True)
    query.join('user')
    pager =  Pager(5, query, request)
    return util.render_to_response(request, 'moderator-board.html', {
        'posts': pager.items,
        'pager': pager,
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
