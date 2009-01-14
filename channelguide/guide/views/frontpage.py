# Copyright (c) 2008 Participatory Culture Foundation
# See LICENSE for details.

import urllib

from django.conf import settings

from channelguide import util, cache
from channelguide.guide import api
from channelguide.guide.models import Channel, Category, Language, PCFBlogPost
from sqlhelper.exceptions import NotFoundError

def _filter_categories(result, count):
    for channel in result:
        if count == 0:
            break
        for cat in channel.categories:
            if cat.on_frontpage == False:
                break
        else:
            count -= 1
            yield channel


def get_current_language(request):
    """
    Returns a Language object for the current language, or None if it's
    the default language.
    """
    if request.LANGUAGE_CODE != settings.LANGUAGE_CODE:
        languageName = settings.LANGUAGE_MAP[request.LANGUAGE_CODE]
        try:
            return Language.query().where(name=languageName).get(
                    request.connection)
        except NotFoundError:
            pass

def get_popular_channels(request, count, language=None):
    query = Channel.query_approved(archived=0, user=request.user)
    lang = get_current_language(request)
    if lang is not None:
        query.where((Channel.c.primary_language_id==lang.id) |
                    Language.secondary_language_exists_where(lang.id))
    query.join('rating')
    query.load('subscription_count_today')
    query.order_by('subscription_count_today', desc=True)
    query.join('categories')
    query.limit(count*30)
    query.cacheable = cache.client
    query.cacheable_time = 300
    result = query.execute(request.connection)
    for r in result:
        if r.rating is None:
            r.star_width = 0
        else:
            r.star_width = r.rating.average * 20
    return _filter_categories(result, count)

def get_featured_channels(request):
    query = Channel.query_approved(featured=1, archived=0, user=request.user)
    return query.order_by('RAND()').execute(request.connection)

def get_new_channels(request, type, count):
    lang = get_current_language(request)
    if lang is not None:
        query = Channel.query_approved(user=request.user)
        query.where(Channel.c.primary_language_id==lang.id)
        query.where(archived=0)
        query.order_by(Channel.c.approved_at, desc=True).limit(count * 3)
        query.load('item_count')
    else:
        query = Channel.query_new(archived=0, user=request.user).load(
                'item_count').limit(count *3)
    if type:
        query.where(Channel.c.url.is_not(None))
    else:
        query.where(Channel.c.url.is_(None))
    query.join('categories')
#    query.cacheable = cache.client
#    query.cacheable_time = 3600
    return list(_filter_categories(query.execute(request.connection), count))

def get_categories(connection):
    return Category.query(on_frontpage=True).order_by('name').execute(connection)

def get_category_channels(request, category):
    category.join('channels').execute(request.connection)
    query = Channel.query_approved(archived=0, user=request.user)
    query.join("categories")
    query.where(Channel.c.id.in_(c.id for c in category.channels))
    query.load('subscription_count_today')
    query.order_by('subscription_count_today', desc=True)
    query.limit(6)
#    query.cacheable = cache.client
#    query.cacheable_time = 300
    popular_channels = []
    for channel in _filter_categories(query.execute(
        request.connection), 2):
        popular_channels.append(channel)
        yield channel

    query = Channel.query_approved(archived=0, user=request.user)
    query.join('categories')
    query.limit(6)
    query.where(Channel.c.id.in_(c.id for c in category.channels))
    if popular_channels:
        query.where(Channel.c.id.not_in(c.id for c in popular_channels))
    query.order_by('RAND()')
    random_channels = list(query.execute(request.connection))
    for channel in _filter_categories(query.execute(request.connection), 2):
        yield channel

def get_adjecent_category(dir, name, connection):
    query = Category.query().load('channel_count')
    if dir == 'after':
        query.where(Category.c.name > name).order_by('name')
    else:
        query.where(Category.c.name < name).order_by('name', desc=True)
    return query.limit(1).get(connection)

# category peeks are windows into categories that show a few (6) channels.
def get_peeked_category(connection, get_params):
    try:
        dir, name = get_params['category_peek'].split(':')
    except:
        query = Category.query().load('channel_count')
        query.where(Category.c.on_frontpage==True)
        return util.select_random(connection, query)[0]
    try:
        return get_adjecent_category(dir, name, connection)
    except LookupError:
        if dir == 'after':
            query = Category.query().order_by('name')
        else:
            query = Category.query().order_by('name', desc=True)
        return query.limit(1).get(connection)

def make_category_peek(request):
    try:
        category = get_peeked_category(request.connection, request.GET)
    except IndexError: # no categories defined
        return None
    name = urllib.quote_plus(category.name)
    return {
            'category': category,
            'channels': get_category_channels(request, category),
            'prev_url': '?category_peek=before:%s' % name,
            'next_url': '?category_peek=after:%s' % name,
            'prev_url_ajax': 'category-peek-fragment?category_peek=before:%s' % name,
            'next_url_ajax': 'category-peek-fragment?category_peek=after:%s' % name,
    }

@cache.cache_for_user
def index(request):
    featured_channels = get_featured_channels(request)

    return util.render_to_response(request, 'frontpage.html', {
        'new_channels': get_new_channels(request, True, 5),
        'popular_channels': get_popular_channels(request, 4),
        'featured_channels': featured_channels[:2],
        'featured_channels_hidden': featured_channels[2:],
        'categories': get_categories(request.connection),
        'category_peek': make_category_peek(request),
        'language' : get_current_language(request),
    })
