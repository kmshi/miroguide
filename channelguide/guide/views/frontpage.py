# Copyright (c) 2008-2009 Participatory Culture Foundation
# See LICENSE for details.


from django.conf import settings

from channelguide import util, cache
from channelguide.guide.models import Channel, Category, Language
from sqlhelper.exceptions import NotFoundError

def _filter_categories(result, count):
    return [channel for channel in result
            if channel.can_appear_on_frontpage()][:count]

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

def get_popular_channels(request, count, language=None, hi_def=None):
    query = Channel.query_approved(archived=0, user=request.user)
    lang = get_current_language(request)
    if lang is not None:
        query.where(Channel.c.primary_language_id==lang.id)
    if hi_def is not None:
        query.where(Channel.c.hi_def==hi_def)
    query.join('rating', 'stats')
    query.order_by(query.joins['stats'].c.subscription_count_today, desc=True)
    query.join('categories')
    query.limit(count*3)
    query.cacheable = cache.client
    query.cacheable_time = 3600
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
    else:
        query = Channel.query_new(archived=0, user=request.user).limit(count *3)
    if type:
        query.where(Channel.c.url.is_not(None))
    else:
        query.where(Channel.c.url.is_(None))
    query.join('categories')
    query.cacheable = cache.client
    query.cacheable_time = 3600
    return _filter_categories(query.execute(request.connection), count)

def get_categories(connection):
    return Category.query(on_frontpage=True).order_by('name').execute(connection)

@cache.cache_for_user
def index(request, show_welcome=False):
    featured_channels = get_featured_channels(request)
    categories = get_categories(request.connection)
    for category in categories:
        channels = category.get_list_channels(request.connection, True)
        category.popular_channels = channels
    return util.render_to_response(request, 'frontpage.html', {
        'show_welcome': show_welcome,
        'new_channels': get_new_channels(request, True, 20),
        'popular_channels': get_popular_channels(request, 20),
        'popular_hd_channels': get_popular_channels(request, 20, hi_def=True),
        'featured_channels': featured_channels[:2],
        'featured_channels_hidden': featured_channels[2:],
        'categories': categories,
        'language' : get_current_language(request),
    })
