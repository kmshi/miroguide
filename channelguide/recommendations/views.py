# Copyright (c) 2008-2009 Participatory Culture Foundation
# See LICENSE for details.

from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator, InvalidPage
from django.shortcuts import render_to_response, get_object_or_404
from django.template.context import RequestContext

from channelguide import api

class RecommendationsObjectList:
    def __init__(self, user, filter):
        self.user = user
        self.filter = filter

    def __len__(self):
        return int(api.utils.get_recommendations(self.user,
                                                 None,
                                                 filter=self.filter))

    def __getslice__(self, offset, end):
        length = end - offset
        return api.utils.get_recommendations(self.user,
                                             offset, length, self.filter)

@login_required
def index(request):
    feed_paginator = Paginator(RecommendationsObjectList(request.user,
                                                         'feed'), 10)
    site_paginator = Paginator(RecommendationsObjectList(request.user,
                                                         'site'), 10)
    try:
        feed_page = feed_paginator.page(request.GET.get('page', 1))
    except InvalidPage:
        feed_page = None
    try:
        site_page = site_paginator.page(request.GET.get('page', 1))
    except InvalidPage:
        site_page = None

    if not feed_page:
        biggest = site_page
    elif not site_page:
        biggest = feed_page
    elif feed_paginator.count > site_paginator.count:
        biggest = feed_page
    else:
        biggest = site_page

    context = {'feed_page': feed_page,
               'site_page': site_page,
               'biggest': biggest,
               'title': "Shows You'll Love;"
               }
    return render_to_response('recommendations/recommend.html',
                              context,
                              context_instance=RequestContext(request))

@login_required
def ratings(request):
    if request.user.is_superuser:
        user = get_object_or_404(User,
                                 pk=request.GET.get('user_id',
                                                    request.user.id))
    else:
        user = request.user
    ratings = api.utils.get_ratings(user)
    return render_to_response('recommendations/user_ratings.html',
                              {'ratings': ratings},
                              context_instance=RequestContext(request))
