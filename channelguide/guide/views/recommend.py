# Copyright (c) 2008 Participatory Culture Foundation
# See LICENSE for details.

from django.core.paginator import Paginator, InvalidPage
from channelguide.guide.models import Rating
from channelguide.guide import api
from channelguide import util
from channelguide.guide.auth import login_required
from channelguide.guide.views.channels import _calculate_pages

class RecommendationsObjectList:
    def __init__(self, connection, user, filter):
        self.connection = connection
        self.user = user
        self.filter = filter

    def __len__(self):
        return int(api.get_recommendations(self.connection, self.user, None,
                                       filter=self.filter))

    def __getslice__(self, offset, end):
        length = end - offset
        return api.get_recommendations(self.connection, self.user, offset,
                                       length, self.filter)

@login_required
def index(request):
    feed_paginator = Paginator(RecommendationsObjectList(request.connection,
                                                         request.user,
                                                         'feed'), 10)
    show_paginator = Paginator(RecommendationsObjectList(request.connection,
                                                         request.user,
                                                         'show'), 10)
    try:
        feed_page = feed_paginator.page(request.GET.get('page', 1))
    except InvalidPage:
        feed_page = None
    try:
        show_page = show_paginator.page(request.GET.get('page', 1))
    except InvalidPage:
        show_page = None

    if not feed_page:
        biggest = show_page
    elif not show_page:
        biggest = feed_page
    elif feed_paginator.count > show_paginator.count:
        biggest = feed_page
    else:
        biggest = show_page
    context = {'feed_page': feed_page,
               'show_page': show_page,
               'pages': _calculate_pages(request, biggest),
               'title': "Shows You'll Love;"
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
