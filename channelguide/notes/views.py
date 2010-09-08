# Copyright (c) 2008-2009 Participatory Culture Foundation
# See LICENSE for details.

from django.core.paginator import Paginator
from django.http import Http404
from django.contrib.auth.decorators import permission_required, login_required
from django.contrib.auth.views import redirect_to_login
from django.shortcuts import render_to_response, get_object_or_404
from django.template.context import RequestContext

from channelguide import util
from channelguide.channels.models import Channel
from channelguide.notes.models import ChannelNote, ModeratorPost

@login_required
def add_note(request):
    try:
        channel_id = int(request.POST['channel-id'])
    except (ValueError, KeyError):
        raise Http404
    channel = get_object_or_404(Channel, pk=channel_id)
    note = ChannelNote.create_note_from_request(request)
    if not request.user.has_perm('notes.add_channelnote') and \
            channel.owner != request.user:
        return redirect_to_login(request.path)
    channel.notes.add(note)
    if request.user != channel.owner:
        note.send_email()
    return util.redirect('channels/%d' % channel.id)

@permission_required('notes.add_moderatorpost')
def moderator_board(request):
    paginator = Paginator(ModeratorPost.objects.all(), 5)
    page = paginator.page(request.GET.get('page', 1))
    return render_to_response('notes/moderator-board.html', {
            'page': page,
            }, context_instance=RequestContext(request))

@permission_required('notes.add_moderatorpost')
def add_moderator_post(request):
    post = ModeratorPost.create_note_from_request(request)
    send_checked = bool(request.POST.get('send-email'))
    post.send_email(send_checked)
    post.save()
    return util.redirect('notes/moderator-board')

@permission_required('notes.delete_moderatorpost')
def post(request, id):
    post = get_object_or_404(ModeratorPost, pk=id)
    if request.method == 'POST':
        if request.POST['action'] == 'delete':
            post.delete()
            return util.redirect_to_referrer(request)
    return util.redirect('notes/moderator-board')
