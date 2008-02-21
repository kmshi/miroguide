from channelguide.guide.models import Channel, Rating
from channelguide.guide import templateutil
from channelguide.guide.auth import moderator_required
from channelguide import util
import operator

@moderator_required
def index(request):
    if request.user.is_admin():
        user_id = int(request.GET.get('user_id', request.user.id))
    else:
        user_id = request.user.id
    ratings = Rating.query(user_id=user_id).execute(request.connection)
    recommendations, reasons = request.user.get_recommendations_from_ratings(
            request.connection, ratings)
    toSort = recommendations.items()
    toSort.sort(key=operator.itemgetter(1), reverse=True)
    ids = [cid for (cid, rating) in toSort[:10]]
    if ids:
        query = Channel.query(Channel.c.id.in_(ids))
        query.join('rating')
        channels = query.execute(request.connection)
        for channel in channels:
            channel.confidence = int(recommendations[channel.id] * 20)
            if channel.confidence == 100:
                channel.confidence = 99 # artificially cap it
            channelReasons = reasons[channel.id][-3:]
            channelReasons = dict((cid, score) for (score, cid) in channelReasons)
            query = Channel.query(Channel.c.id.in_(channelReasons.keys()))
            channel.reasons = query.execute(request.connection)
            for reason in channel.reasons:
                reason.score = channelReasons[reason.id]
            channel.reasons = list(channel.reasons)
            channel.reasons.sort(key=operator.attrgetter('score'), reverse=True)
        channels = list(channels)
        channels.sort(key=operator.attrgetter('confidence'), reverse=True)
    else:
        channels = []
    context = {'channels': channels,
            'title': "Channels You'll &hearts;"
        }
    return util.render_to_response(request, 'recommend.html', context)

@moderator_required
def ratings(request):
    query = Rating.query(user_id=request.user.id)
    query.order_by('rating', desc=True)
    query.join('channel')
    context = {'ratings':query.execute(request.connection)}
    return util.render_to_response(request, 'user_ratings.html', context)
