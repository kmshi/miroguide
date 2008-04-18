# Copyright (c) 2008 Participatory Culture Foundation
# See LICENSE for details.

from channelguide.guide.models import Channel, Rating
from channelguide.guide import templateutil, recommendations, api
from channelguide import util
from channelguide.guide.auth import login_required

class RecommendationsPager(templateutil.ManualPager):

    def __init__(self, items_per_page, request):
        self.request = request

        templateutil.ManualPager.__init__(self, items_per_page,
                                          api.get_recommendations(
                self.request.connection, self.request.user, None),
                                          self._items_callback, request)
        if self.links.next:
            self.links.next['text'] = 'More Recommendations &gt;&gt;'

    def _items_callback(self, start, length):
        return api.get_recommendations(self.request.connection,
                                       self.request.user,
                                       start, length)

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
