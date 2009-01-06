# Copyright (c) 2008-2009 Participatory Culture Foundation
# See LICENSE for details.

from django.http import Http404

from channelguide import cache
from channelguide.guide.views.channels import filtered_listing

@cache.aggresively_cache('search')
def search(request):
    context = {}
    try:
        search_query = request.GET['query']
    except KeyError:
        raise Http404

    return filtered_listing(request, search_query, 'search', title=search_query)
