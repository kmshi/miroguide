# Copyright (c) 2008 Participatory Culture Foundation
# See LICENSE for details.

import re

from django.utils.translation import gettext as _
from django.http import Http404

from channelguide import util, cache
from channelguide.guide import search as search_mod
from channelguide.guide.models import Channel

PAGE_LIMIT = 10
SIDEBAR_LIMIT = 4

def get_search_terms(query):
    return [term for term in re.split("\s", query.strip())]

def terms_too_short(terms):
    return len([term for term in terms if len(term) >= 3]) == 0

def mod_sees_approved(function):
    def _(request, terms):
        query = function(terms)
        if not request.user.is_moderator():
            query.where(state=Channel.APPROVED)
        return query
    return _

search_feeds = mod_sees_approved(search_mod.search_feeds)
search_shows = mod_sees_approved(search_mod.search_shows)
search_items = mod_sees_approved(search_mod.search_items)

@cache.aggresively_cache('search')
def search(request):
    context = {}
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
        return util.render_to_response(request, 'search.html', {
            'results_count': 0,
            'search_terms': terms,
            'search_query': search_query,
            'terms_too_short': True,
            })
    terms = [t for t in terms if len(t) >= 3]
    feeds_query = search_feeds(request, terms)
    shows_query = search_shows(request, terms)

    search_type = request.GET.get('type')

    results_query, sidebar_query = feeds_query, shows_query
    results_type, sidebar_type = 'video feeds', 'streaming shows'
    results_class, sidebar_class = 'rss', 'streaming'
    sidebar_url = util.make_absolute_url(request.path,
                                         {'query': search_query,
                                          'type': 'shows'})
    comprehensive_query = search_items(request, terms)
    comprehensive_url = util.make_absolute_url(request.path,
                                               {'query': search_query,
                                                'type': 'comprehensive'})

    if search_type == 'shows':
        results_query, sidebar_query = sidebar_query, results_query
        results_type, sidebar_type = sidebar_type, results_type
        results_class, sidebar_class = sidebar_class, results_class
        sidebar_url = util.make_absolute_url(request.path,
                                             {'query': search_query,
                                              'type': 'feeds'})
    elif search_type == 'comprehensive':
        results_query = comprehensive_query
        results_type = 'videos'
        comprehensive_url = None
    else:
        search_type = 'feeds'

    results_count = results_query.count(request.connection)
    if results_count:
        results_query.load('subscription_count_month').limit(
            PAGE_LIMIT).offset((page - 1) * PAGE_LIMIT)
        results = results_query.execute(request.connection)
        if not results:
            raise Http404 # page too high
        results.join('items', 'rating').execute(request.connection)
        if results_count > page * PAGE_LIMIT:
            results_next_url = util.make_absolute_url(request.path,
                                                      {'query': search_query,
                                                       'type': search_type,
                                                       'page': str(page + 1)})
        else:
            results_next_url = None
        if page == 1:
            results_intro = 'First <strong>%i</strong>' % len(results)
        else:
            results_intro = '<strong>%i</strong> - <strong>%i</strong>' % (
                page * PAGE_LIMIT - PAGE_LIMIT + 1, page * PAGE_LIMIT)
        results_intro = util.mark_safe(results_intro)
    else:
        results_intro = util.mark_safe('<strong>0</strong>')
        results_next_url = None
        results = []

    sidebar = sidebar_query.limit(SIDEBAR_LIMIT).execute(request.connection)
    sidebar_count = sidebar_query.count(request.connection)
    if len(sidebar) == sidebar_count:
        sidebar_url = None

    if comprehensive_url:
        comprehensive_count = comprehensive_query.count(request.connection)
    else:
        comprehensive_count = None

    if results_count == 1 and sidebar_count == 0:
        return util.redirect(results[0].get_absolute_url())

    if sidebar_count == 1 and results_count == 0:
        return util.redirect(sidebar[0].get_absolute_url())

    return util.render_to_response(request, 'search.html', {
        'results': results,
        'intro': results_intro,
        'count': results_count,
        'title': results_type,
        'header_class': results_class,
        'next_page': results_next_url,

        'sidebar': sidebar,
        'sidebar_count': sidebar_count,
        'sidebar_type': sidebar_type,
        'sidebar_class': sidebar_class,
        'sidebar_url': sidebar_url,

        'comprehensive_count': comprehensive_count,
        'comprehensive_url': comprehensive_url,

        'search_terms': terms,
        'search_query': search_query,
        'page': page,
        })
