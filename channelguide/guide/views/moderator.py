from channelguide import util
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

    context['new_count'] = count_for_state(request.connection, Channel.NEW)
    context['dont_know_count'] = count_for_state(request.connection,
            Channel.DONT_KNOW)
    context['waiting_count'] = count_for_state(request.connection,
            Channel.WAITING)
    context['rejected_count'] = count_for_state(request.connection,
            Channel.REJECTED)

    query = ModeratorPost.query().order_by('created_at', desc=True)
    query.join('user')
    context['latest_posts'] = query.limit(5).execute(request.connection)
    context['post_count'] = ModeratorPost.query().count(request.connection)

    return util.render_to_response(request, 'moderate.html', context)

@moderator_required
def how_to_moderate(request):
    return util.render_to_response(request, 'how-to-moderate.html')
