from channelguide import util
from channelguide.guide import templateutil
from channelguide.guide.auth import moderator_required
from channelguide.guide.models import Channel, ModeratorPost

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

    query = ModeratorPost.query().order_by('created_at', desc=True)
    query.join('user')
    context['latest_posts'] = query.limit(5).execute(request.connection)
    context['post_count'] = ModeratorPost.query().count(request.connection)

    return util.render_to_response(request, 'moderate.html', context)

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
