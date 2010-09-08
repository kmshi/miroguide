# Copyright (c) 2008-2009 Participatory Culture Foundation
# See LICENSE for details.

from django.conf import settings

from channelguide import util
from channelguide.cache.decorators import cache_for_user
from channelguide.channels.models import Channel
from channelguide.labels.models import Category, Language

def _filter_categories(result, count):
    return result.exclude(categories__on_frontpage=False)[:count]

def get_current_language(request):
    """
    Returns a Language object for the current language, or None if it's
    the default language.
    """
    if not hasattr(request, '_current_language_cache'):
        language_code = request.LANGUAGE_CODE
        if request.user.is_authenticated():
            language_code = request.user.get_profile().language
            if not request.user.get_profile().filter_languages:
                request._current_language_cache = None
                return
        languageName = settings.LANGUAGE_MAP[language_code]
        try:
            request._current_language_cache = Language.objects.get(
                name=languageName)
        except Language.DoesNotExist:
            request._current_language_cache = None
    return request._current_language_cache


class FrontpageView:

    show_state = None
    additional_context = {'audio': False}

    @classmethod
    def get_popular_channels(klass, request, count, language=None,
                             hi_def=None):
        query = Channel.objects.filter(state=klass.show_state, archived=0)
        lang = get_current_language(request)
        if lang is not None:
            query = query.filter(language=lang)
        if hi_def is not None:
            query = query.filter(hi_def=hi_def)
        query = query.order_by('-stats__subscription_count_today')
        return _filter_categories(query, count)

    @classmethod
    def get_featured_channels(klass, request):
        query = Channel.objects.approved(state=klass.show_state,
                                         featured=1, archived=0)
        return query.order_by('?')

    @classmethod
    def get_new_channels(klass, request, type, count):
        lang = get_current_language(request)
        if lang is not None:
            query = Channel.objects.filter(state=klass.show_state,
                                           language=lang)
            query = query.order_by('-approved_at')
        else:
            query = Channel.objects.new(state=klass.show_state, archived=0)
        if type:
            query = query.filter(url__isnull=False)
        else:
            query = query.filter(url__isnull=True)

        return _filter_categories(query, count)

    @classmethod
    def __call__(klass, request, show_welcome):
        featured_channels = list(klass.get_featured_channels(request))
        categories = Category.objects.filter(
            on_frontpage=True).order_by('name')
        language = get_current_language(request)
        for category in categories:
            def popular_channels(category=category):
                return category.get_list_channels(True, klass.show_state,
                                                  language)
            category.popular_channels = popular_channels
        context = {
            'show_welcome': show_welcome,
            'new_channels': klass.get_new_channels(request, True, 20),
            'popular_channels': klass.get_popular_channels(request, 20),
            'popular_hd_channels': klass.get_popular_channels(request, 20,
                                                              hi_def=True),
            'featured_channels': featured_channels[:2],
            'featured_channels_hidden': featured_channels[2:],
            'categories': categories,
            'language' : language,
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

@cache_for_user
def index(request, show_welcome=False):
    return video_frontpage(request, show_welcome)

@cache_for_user
def audio_index(request, show_welcome=False):
    return audio_frontpage(request, show_welcome)
