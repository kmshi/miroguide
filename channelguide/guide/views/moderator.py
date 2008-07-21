# Copyright (c) 2008 Participatory Culture Foundation
# See LICENSE for details.

from django.http import Http404
from django.utils.translation import gettext as _

from channelguide import util
from channelguide.guide import templateutil
from channelguide.guide.auth import moderator_required
from channelguide.guide.models import Channel, ModeratorPost, FeaturedQueue

def count_for_state(connection, state):
    return Channel.query(state=state).count(connection)

@moderator_required
def index(request):
    context = {}

    query = Channel.query(Channel.c.moderator_shared_at.is_not(None))
    query.order_by('moderator_shared_at', desc=True).limit(5)
    context['shared_channels'] = query.execute(request.connection)
    for channel in context['shared_channels']:
        channel.update_moderator_shared_by(request.connection)

    context['new_count'] = count_for_state(request.connection, Channel.NEW)
    context['dont_know_count'] = count_for_state(request.connection,
            Channel.DONT_KNOW)
    waiting_q = Channel.query(Channel.c.waiting_for_reply_date.is_not(None))
    context['waiting_count'] = waiting_q.count(request.connection)
    context['suspended_count'] = count_for_state(request.connection,
            Channel.SUSPENDED)
    context['rejected_count'] = count_for_state(request.connection,
            Channel.REJECTED)
    context['featured_count'] = FeaturedQueue.query(FeaturedQueue.c.state==0).count(request.connection)
    
    query = ModeratorPost.query().order_by('created_at', desc=True)
    query.join('user')
    context['latest_posts'] = query.limit(5).execute(request.connection)
    context['post_count'] = ModeratorPost.query().count(request.connection)

    return util.render_to_response(request, 'moderate.html', context)

@moderator_required
def channel_list(request, state):
    query = Channel.query().join('owner').order_by('creation_time')
    if state == 'waiting':
        query.where(Channel.c.waiting_for_reply_date.is_not(None))
        query.order_by('waiting_for_reply_date')
        header = _("Channels Waiting For Replies")
    elif state == 'dont-know':
        query.where(state=Channel.DONT_KNOW)
        header = _("Channels Flagged Don't Know By a Moderator")
    elif state == 'rejected':
        query.where(state=Channel.REJECTED)
        header = _("Rejected Channels")
    elif state == 'suspended':
        query.where(state=Channel.SUSPENDED)
        header = _("Suspended Channels")
    elif state == 'featured':
        query.join('featured_queue')
        query.where(query.joins['featured_queue'].c.state == FeaturedQueue.IN_QUEUE)
        header = _("Featured Queue")
    else:
        query.where(state=Channel.NEW)
        header = _("Unreviewed Channels")
    count = query.count(request.connection)
    try:
        page = int(request.GET.get('page', 1))
    except ValueError:
        raise Http404
    if page * 10 < count:
        next_page = request.path + '?page=%i' % (page + 1)
    else:
        next_page = None
    channels = query.limit(10).offset((page - 1) * 10).execute(request.connection)
    print channels
    if len(channels) == 0:
        raise Http404
    if page == 1:
        intro = 'First %i' % len(channels)
    else:
        intro = '%i - %i' (page * 10 - 11, min(page * 10, count))

    return util.render_to_response(request, 'listing.html', {
        'results': channels,
        'count': count,
        'title': header,
        'header_class': '',
        'intro': intro,
        'page': page,
        'next_page': next_page})

@moderator_required
def shared(request):
    query = Channel.query(Channel.c.moderator_shared_at.is_not(None))
    query.order_by('moderator_shared_at', desc=True)
    pager = templateutil.Pager(10, query, request)
    for channel in pager.items:
        channel.update_moderator_shared_by(request.connection)

    return util.render_to_response(request, "shared.html", {
        'pager': pager
        })

@moderator_required
def how_to_moderate(request):
    return util.render_to_response(request, 'how-to-moderate.html')
