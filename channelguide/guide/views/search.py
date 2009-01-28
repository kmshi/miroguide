# Copyright (c) 2008-2009 Participatory Culture Foundation
# See LICENSE for details.

import re

from django.http import Http404

from channelguide import util, cache
from channelguide.guide.views.channels import filtered_listing

def get_search_terms(query):
    return [term for term in re.split("\s", query.strip())]

def terms_too_short(terms):
    return len([term for term in terms if len(term) >= 3]) == 0


@cache.aggresively_cache('search')
def search(request):
    try:
        search_query = request.GET['query']
    except KeyError:
        raise Http404

    try:
        page = int(request.GET.get('page', 1))
    except ValueError:
        raise Http404

    search_query = search_query.strip()
    terms = get_search_terms(search_query)
    if terms_too_short(terms):
        return util.render_to_response(request, 'channel-search.html', {
            #'results_count': 0,
            'search_terms': terms,
            'search_query': search_query,
            'terms_too_short': True,
            })

    return filtered_listing(request, search_query, 'search', title=search_query)
