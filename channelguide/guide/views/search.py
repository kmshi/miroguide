from cgi import escape
import urllib
import re

from django.utils.translation import gettext as _
from django.http import Http404

from channelguide import util, cache
from channelguide.guide.search import search_channels, search_items
from channelguide.guide.templateutil import Pager
from channelguide.guide.models import (Channel, Category, Tag, Item, Language,
        ChannelSearchData, ItemSearchData)

FRONT_PAGE_LIMIT = 10
FRONT_PAGE_LIMIT_ITEMS = 20

def get_search_terms(query):
    return [term for term in re.split("\s", query.strip())]

def terms_too_short(terms):
    return len([term for term in terms if len(term) >= 3]) == 0

def more_results_link(query, total_results):
    href = 'search-more-channels?query=' + urllib.quote_plus(query)
    label = _('%d More Matching Channels >>') % (total_results -
            FRONT_PAGE_LIMIT)
    return util.make_link(href, escape(label))

def more_results_link_items(query, total_results):
    href = 'search-more-items?query=' + urllib.quote_plus(query)
    label = _('%d More Matching Channel Videos >>') % (total_results -
            FRONT_PAGE_LIMIT_ITEMS)
    return util.make_link(href, escape(label))

def search_results(connection, class_, terms, search_attribute='name'):
    query = class_.query().load('channel_count')
    query.having(class_.c.channel_count > 0)

    search_column = class_.c.get(search_attribute)
    for term in terms:
        query.where(search_column.like('%s%%' % term))
    return query.execute(connection)

@cache.aggresively_cache
def search(request):
    context = {}

    try:
        search_query = request.GET['query']
    except:
        raise Http404
    search_query = search_query.strip()
    terms = get_search_terms(search_query)
    if terms_too_short(terms):
        return util.render_to_response(request, 'channel-search.html', {
            'results_count': 0,
            'search_query': search_query,
            })

    query = search_channels(terms)
    results_count = query.count(request.connection)
    results = query.limit(FRONT_PAGE_LIMIT).execute(request.connection)

    query = search_items(terms)
    item_results_count = query.count(request.connection)
    item_results = query.limit(FRONT_PAGE_LIMIT_ITEMS).execute(request.connection)

    return util.render_to_response(request, 'channel-search.html', {
        'results': results,
        'results_count': results_count,
        'item_results': item_results,
        'item_results_count': item_results_count,
        'extra_results': results_count > FRONT_PAGE_LIMIT,
        'extra_item_results': item_results_count > FRONT_PAGE_LIMIT_ITEMS,
        'tags': search_results(request.connection, Tag, terms),
        'languages': search_results(request.connection, Language, terms),
        'categories': search_results(request.connection, Category, terms),
        'search_query': search_query,
        'more_results_link': more_results_link(search_query, results_count),
        'more_results_link_items': more_results_link_items(search_query, 
            item_results_count),
        })

def do_search_more(request, title, search_func):
    try:
        search_query = request.GET['query']
    except:
        raise Http404
    terms = get_search_terms(search_query)
    if terms_too_short(terms):
        return util.render_to_response(request, 'search-more.html', {})
    search_query = search_query.strip()
    query = search_func(terms)
    pager = Pager(20, query, request)
    return util.render_to_response(request, 'search-more.html', {
        'title': title % search_query,
        'search_query': search_query,
        'results': pager.items,
        'pager': pager,
        })

@cache.aggresively_cache
def search_more(request):
    title = _('Channels Matching %s')
    return do_search_more(request, title, search_channels)

@cache.aggresively_cache
def search_more_items(request):
    title = _('Channels With Videos Matching %s')
    return do_search_more(request, title, search_items)
