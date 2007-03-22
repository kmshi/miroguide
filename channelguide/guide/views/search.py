from cgi import escape
import urllib
import re

from django.utils.translation import gettext as _

from channelguide import util
from channelguide.guide.templateutil import ManualPager
from channelguide.guide.models import Channel, Category, Tag, Item, Language

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

def search_results(session, class_, terms, search_attribute='name'):
    select = session.query(class_).select()
    if class_ is not Language:
        select = select.filter(class_.c.channel_count > 0)
    else:
        select = select.filter((class_.c.channel_count_primary > 0) |
                (class_.c.channel_count_secondary > 0))

    search_column = class_.c[search_attribute]
    for term in terms:
        select = select.filter(search_column.like('%s%%' % term))
    return select.list()

def search(request):
    try:
        query = request.GET['query']
    except:
        raise Http404
    query = query.strip()

    terms = get_search_terms(query)
    if terms_too_short(terms):
        return util.render_to_response(request, 'channel-search.html', {
            'results_count': 0,
            'search_query': query,
            })

    results = Channel.search(request.db_session, terms, limit=FRONT_PAGE_LIMIT)
    results_count = Channel.search_count(request.connection, terms)
    item_results = Channel.search_items(request.db_session, terms,
            limit=FRONT_PAGE_LIMIT_ITEMS)
    item_results_count = Channel.search_items_count(request.connection, terms)

    return util.render_to_response(request, 'channel-search.html', {
        'results': results,
        'results_count': results_count,
        'item_results': item_results,
        'item_results_count': item_results_count,
        'extra_results': results_count > FRONT_PAGE_LIMIT,
        'extra_item_results': item_results_count > FRONT_PAGE_LIMIT_ITEMS,
        'tags': search_results(request.db_session, Tag, terms),
        'languages': search_results(request.db_session, Language, terms),
        'categories': search_results(request.db_session, Category, terms),
        'search_query': query,
        'more_results_link': more_results_link(query, results_count),
        'more_results_link_items': more_results_link_items(query, 
            item_results_count),
        })

def do_search_more(request, title, search_func, search_count_func):
    try:
        query = request.GET['query']
    except:
        raise Http404

    terms = get_search_terms(query)
    if terms_too_short(terms):
        return util.render_to_response(request, 'search-more.html', {})
    search_query = query.strip()
    total_results = search_count_func(request.connection, terms)
    def callback(offset, limit):
        return search_func(request.db_session, terms, offset, limit)
    pager = ManualPager(20, total_results, callback, request)
    return util.render_to_response(request, 'search-more.html', {
        'title': title % search_query,
        'search_query': search_query,
        'results': pager.items,
        'pager': pager,
        })

def search_more(request):
    title = _('Channels Matching %s')
    return do_search_more(request, title, Channel.search, Channel.search_count)

def search_more_items(request):
    title = _('Channels With Videos Matching %s')
    return do_search_more(request, title, Channel.search_items,
            Channel.search_items_count)
