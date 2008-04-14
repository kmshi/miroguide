# Copyright (c) 2008 Participatory Culture Foundation
# See LICENSE for details.

from channelguide.guide.models import Channel, Rating
from channelguide.guide import templateutil, recommendations
from channelguide import util
from channelguide.guide.auth import login_required
from channelguide.cache import client
import operator

class RecommendationsPager(templateutil.ManualPager):

    def __init__(self, items_per_page, request):
        self.request = request

        if request.user.is_admin():
            user_id = int(request.GET.get('user_id', request.user.id))
        else:
            user_id = request.user.id
        query = Rating.query(user_id=user_id).order_by(Rating.c.timestamp)
        ratings = query.execute(request.connection)
        if ratings:
            cacheKey = ':'.join(('recommendations_for', str(user_id),
                str(ratings[-1].timestamp.isoformat())))
            result = client.get(cacheKey)
            if result is None:
                (channels,
                    reasons) = recommendations.get_recommendations_from_ratings(
                        request.connection, ratings)
                toSort = channels.items()
                toSort.sort(key=operator.itemgetter(1), reverse=True)
                self.recommendations = channels
                self.reasons = reasons
                ids = [cid for (cid, rating) in toSort if rating>=3.25]
                self.ids = ids[:10 * items_per_page]
                for id in self.recommendations.keys():
                    if id not in self.ids:
                        del self.recommendations[id]
                        del self.reasons[id]
                result = self.recommendations, self.reasons, self.ids
                client.set(cacheKey, result)
            else:
                self.recommendations, self.reasons, self.ids = result
        else:
            self.ids = []
        templateutil.ManualPager.__init__(self, items_per_page, len(self.ids),
                self._items_callback, request)
        if self.links.next:
            self.links.next['text'] = 'More Recommendations &gt;&gt;'

    def _items_callback(self, start, length):
        ids = self.ids[start:start+length]
        if ids:
            query = Channel.query(Channel.c.id.in_(ids))
            query.join('rating')
            channels = query.execute(self.request.connection)
            for channel in channels:
                channel.guessed = self.recommendations[channel.id]
                if channel.id in self.reasons:
                    channelReasons = self.reasons[channel.id][-3:]
                    channelReasons = dict((cid, score) for (score, cid) in channelReasons)
                    query = Channel.query(Channel.c.id.in_(channelReasons.keys()))
                    channel.reasons = query.execute(self.request.connection)
                    for reason in channel.reasons:
                        reason.score = channelReasons[reason.id]
                    channel.reasons = list(channel.reasons)
                    channel.reasons.sort(key=operator.attrgetter('score'), reverse=True)
            channels = list(channels)
            channels.sort(key=operator.attrgetter('guessed'), reverse=True)
            return channels
        else:
            return []

@login_required
def index(request):
    recommendations = bool('test' not in request.GET)
    pager = RecommendationsPager(10, request)
    if not pager.items and recommendations:
        recommendations = False
        query = Channel.query_approved(user=request.user)
        query.join('rating')
        query.load('subscription_count_month', 'item_count')
        query.order_by(query.get_column('subscription_count_month'), desc=True)
        pager = templateutil.Pager(10, query, request)
        for channel in pager.items:
                channel.timeline = 'This Month'
                channel.popular_count = getattr(channel,
                                                'subscription_count_month')
    context = {'pager': pager,
               'recommendations': recommendations,
               'title': "Channels You'll &hearts;"
               }
    return util.render_to_response(request, 'recommend.html', context)

@login_required
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
