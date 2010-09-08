# Copyright (c) 2008-2009 Participatory Culture Foundation
# See LICENSE for details.

import re

from django.http import Http404
from django.shortcuts import render_to_response
from django.template.context import RequestContext

from channelguide.channels.views import filtered_listing
from channelguide.cache.decorators import cache_with_sites
def get_search_terms(query):
    return [term for term in re.split("\s", query.strip())]

def terms_too_short(terms):
    return len([term for term in terms if len(term) >= 3]) == 0

@cache_with_sites('search')
def search(request):
    try:
        search_query = request.GET['query']
    except KeyError:
        raise Http404

    search_query = search_query.strip()
    terms = get_search_terms(search_query)
    if terms_too_short(terms):
        return render_to_response('channels/listing.html', {
                #'results_count': 0,
                'search_terms': terms,
                'search_query': search_query,
                'terms_too_short': True,
                },
                                  context_instance=RequestContext(request))


    return filtered_listing(request, search_query, 'search', title='%(value)s')
