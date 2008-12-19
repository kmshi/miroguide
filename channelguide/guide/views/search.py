# Copyright (c) 2008 Participatory Culture Foundation
# See LICENSE for details.

import re

from django.utils.translation import gettext as _
from django.http import Http404

from channelguide import util, cache
from channelguide.guide import search as search_mod
from channelguide.guide.templateutil import Pager
from channelguide.guide.models import Channel, Category, Tag, Item, Language

PAGE_LIMIT = 10
SIDEBAR_LIMIT = 4

def get_search_terms(query):
    return [term for term in re.split("\s", query.strip())]

def terms_too_short(terms):
    return len([term for term in terms if len(term) >= 3]) == 0

def search_channels(request, terms, is_feed=True):
    query = search_mod.search_channels(terms)
    if not request.user.is_moderator():
        query.where(state=Channel.APPROVED)
    return query

def search_results(connection, class_, terms, search_attribute='name'):
    query = class_.query().load('channel_count')
    query.having(class_.c.channel_count > 0)

    search_column = class_.c.get(search_attribute)
    for term in terms:
        query.where(search_column.like('%s%%' % term.encode('utf8')))
    return query.execute(connection)

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
        return util.render_to_response(request, 'channel-search.html', {
            #'results_count': 0,
            'search_terms': terms,
            'search_query': search_query,
            'terms_too_short': True,
            })
    terms = [t for t in terms if len(t) >= 3]
    query = search_channels(request, terms)
    channel_pager = Pager(20, query, request)

    tags = search_results(request.connection, Tag, terms)
    languages = search_results(request.connection, Language, terms)
    categories = search_results(request.connection, Category, terms)

    return util.render_to_response(
        request,
        'channel-search.html',
        {'channel_pager': channel_pager,
         'tags': tags,
         'languages': languages,
         'categories': categories,
         'search_terms': terms,
         'search_query': search_query,
        })
