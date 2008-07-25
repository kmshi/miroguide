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

def get_featured_channels(request):
    query = Channel.query_approved(featured=1, archived=0, user=request.user)
    return query.order_by('RAND()').execute(request.connection)

def get_new_channels(request, type, count):
    lang = get_current_language(request)
    if lang is not None:
        query = Channel.query_approved(user=request.user)
        query.where((Channel.c.primary_language_id==lang.id) |
                    Language.secondary_language_exists_where(lang.id))
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
    print query
    query.join('categories')
#    query.cacheable = cache.client
#    query.cacheable_time = 3600
    return _filter_categories(query.execute(request.connection), count)

@cache.cache_for_user
def index(request):
    if not request.user.is_authenticated():
        title = _("What is Miro?")
        desc = _("Miro is an easy way to subscribe and watch all of these shows.  Using it is 100% free.")
        link = _("Download Miro")
        request.add_notification(None, '<span class="only-in-miro"><center>Rate channels to get <a href="/recommend/">personalized recommendations</a>!</center></span><span class="only-in-browser"><strong>%s</strong> %s <a href="http://www.getmiro.com/download">%s</a></span>' % (title, desc, link))

    context = {
        'feed': get_new_channels(request, True, 4),
        'streaming': get_new_channels(request, False, 4),
        'featured': get_featured_channels(request),
        'recommended': [],
        }
    if request.user.is_authenticated():
        context['recommended'] = api.get_recommendations(request.connection,
                                                         request.user,
                                                         length=2)

    return util.render_to_response(request, 'index.html', context)
