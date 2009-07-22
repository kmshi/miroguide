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

def get_categories(connection):
        return Category.query(on_frontpage=True).order_by('name').execute(connection)


class FrontpageView:

    show_state = None
    additional_context = {}

    @classmethod
    def get_popular_channels(klass, request, count, language=None, hi_def=None):
        query = Channel.query(archived=0, user=request.user)
        query.where(Channel.c.state == klass.show_state)
        lang = get_current_language(request)
        if lang is not None:
            query.where(Channel.c.primary_language_id==lang.id)
        if hi_def is not None:
            query.where(Channel.c.hi_def==hi_def)
        query.join('categories', 'stats')
        query.order_by(query.joins['stats'].c.subscription_count_today, desc=True)
        query.limit(count*3)
        query.cacheable = cache.client
        query.cacheable_time = 3600
        result = query.execute(request.connection)
        return list(_filter_categories(result, count))

    @classmethod
    def get_featured_channels(klass, request):
        query = Channel.query(featured=1, archived=0, user=request.user)
        query.where(Channel.c.state == klass.show_state)
        return query.order_by('RAND()').execute(request.connection)

    @classmethod
    def get_new_channels(klass, request, type, count):
        lang = get_current_language(request)
        if lang is not None:
            query = Channel.query(user=request.user)
            query.where(Channel.c.state == klass.show_state)
            query.where(Channel.c.primary_language_id==lang.id)
            query.where(archived=0)
            query.order_by(Channel.c.approved_at, desc=True).limit(count * 3)
        else:
            query = Channel.query_new(state=klass.show_state, archived=0,
                                      user=request.user).limit(count *3)
        if type:
            query.where(Channel.c.url.is_not(None))
        else:
            query.where(Channel.c.url.is_(None))
        query.join('categories')
        query.cacheable = cache.client
        query.cacheable_time = 3600
        return list(_filter_categories(query.execute(request.connection), count))

    @classmethod
    def __call__(klass, request, show_welcome):
        featured_channels = klass.get_featured_channels(request)
        categories = get_categories(request.connection)
        for category in categories:
            category.popular_channels = category.get_list_channels(
                request.connection, True, klass.show_state)
        context = {
            'show_welcome': show_welcome,
            'new_channels': klass.get_new_channels(request, True, 20),
            'popular_channels': klass.get_popular_channels(request, 20),
            'popular_hd_channels': klass.get_popular_channels(request, 20, hi_def=True),
            'featured_channels': featured_channels[:2],
            'featured_channels_hidden': featured_channels[2:],
            'categories': categories,
            'language' : get_current_language(request),
        }
        context.update(klass.additional_context)
        return util.render_to_response(request, 'frontpage.html', context)

class VideoFrontpage(FrontpageView):
    show_state = Channel.APPROVED

class AudioFrontpage(FrontpageView):
    show_state = Channel.AUDIO
    additional_context = {
        'audio': True
        }

video_frontpage = VideoFrontpage()
audio_frontpage = AudioFrontpage()

@cache.cache_for_user
def index(request, show_welcome=False):
    return video_frontpage(request, show_welcome)

@cache.cache_for_user
def audio_index(request, show_welcome=False):
    return audio_frontpage(request, show_welcome)
