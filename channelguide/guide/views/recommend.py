from channelguide.guide.models import Channel, Rating
from channelguide.guide import templateutil
from channelguide.guide.auth import beta_required
from channelguide import util
import operator

class RecommendationsPager(templateutil.ManualPager):

    def __init__(self, items_per_page, request):
        self.request = request

        if request.user.is_admin():
            user_id = int(request.GET.get('user_id', request.user.id))
        else:
            user_id = request.user.id
        ratings = Rating.query(user_id=user_id).execute(request.connection)
        (recommendations,
            reasons) = request.user.get_recommendations_from_ratings(
                request.connection, ratings)
        toSort = recommendations.items()
        toSort.sort(key=operator.itemgetter(1), reverse=True)
        self.recommendations = recommendations
        self.reasons = reasons
        ids = [cid for (cid, rating) in toSort if rating>=3.25]
        self.ids = ids[:10 * items_per_page]
        templateutil.ManualPager.__init__(self, items_per_page, len(self.ids),
                self._items_callback, request)

    def _items_callback(self, start, length):
        ids = self.ids[start:start+length]
        if ids:
            query = Channel.query(Channel.c.id.in_(ids))
            query.join('rating')
            channels = query.execute(self.request.connection)
            for channel in channels:
                channel.confidence = int(self.recommendations[channel.id] * 20)
                if channel.confidence == 100:
                    channel.confidence = 99 # artificially cap it
                channelReasons = self.reasons[channel.id][-3:]
                channelReasons = dict((cid, score) for (score, cid) in channelReasons)
                query = Channel.query(Channel.c.id.in_(channelReasons.keys()))
                channel.reasons = query.execute(self.request.connection)
                for reason in channel.reasons:
                    reason.score = channelReasons[reason.id]
                channel.reasons = list(channel.reasons)
                channel.reasons.sort(key=operator.attrgetter('score'), reverse=True)
            channels = list(channels)
            channels.sort(key=operator.attrgetter('confidence'), reverse=True)
            return channels
        else:
            return []

@beta_required
def index(request):
    pager = RecommendationsPager(10, request)
    context = {'pager': pager,
            'title': "Channels You'll &hearts;"
        }
    return util.render_to_response(request, 'recommend.html', context)

@beta_required
def ratings(request):
    if request.user.is_admin():
        user_id = request.GET.get('user_id', request.user.id)
    else:
        user_id = request.user.id
    query = Rating.query(user_id=user_id)
    query.order_by('rating', desc=True)
    query.join('channel')
    context = {'ratings':query.execute(request.connection)}
    return util.render_to_response(request, 'user_ratings.html', context)
