# Copyright (c) 2009 Participatory Culture Foundation
# See LICENSE for details.

import simplejson
from itertools import izip, count
import sha
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ObjectDoesNotExist
from django.http import HttpResponse, Http404
from django.shortcuts import render_to_response
from django.template.context import RequestContext
from django.utils.importlib import import_module
from django.utils.translation import ugettext as _

from channelguide import util
from channelguide.cache.decorators import api_cache
from channelguide.api import utils as api_utils

def requires_arguments(*arguments):
    def outer(func):
        def wrapper(request):
            for name in arguments:
                if name not in request.REQUEST:
                    return error_response(request, 'MISSING_ARGUMENT',
                                          'You forgot the "%s" argument'
                                          % name)
            return func(request)
        return util.copy_function_metadata(wrapper, func)
    return outer

def requires_login(func):
    def wrapper(request):
        error = error_response(request, 'INVALID_SESSION',
                               'Invalid session', 403)
        if 'session' not in request.REQUEST:
            return error
        session_key = request.REQUEST['session']
        engine = import_module(settings.SESSION_ENGINE)
        session = engine.SessionStore(session_key)

        if 'apiUser' not in session:
            return error
        session.set_expiry(None)
        request.user = api_utils.login(
            session['apiUser'])

        return func(request)
    return util.copy_function_metadata(wrapper, func)

def data_for_channel(channel):
    default_keys = ('id', 'name', 'description', 'url', 'website_url',
            'hi_def', 'publisher', 'postal_code')
    data = dict((key, getattr(channel, key)) for key in default_keys)
    data['details_url'] = channel.get_absolute_url()
    data['subscribe_url'] = channel.get_subscription_url()
    data['subscribe_hit_url'] = channel.get_subscribe_hit_url()
    if channel.thumbnail_exists():
        data['thumbnail_url'] = channel.thumb_url(370, 247)
    data['language'] = channel.language.name
    data['category'] =  tuple(
        channel.categories.values_list('name', flat=True))
    data['tag'] = tuple(
        channel.tags.values_list('name', flat=True))
    data['item'] = [data_for_item(item) for item in channel.items.all()]
    try:
        data['subscription_count_today'] = \
            channel.stats.subscription_count_today
    except ObjectDoesNotExist:
        pass
    else:
        data['subscription_count_month'] = \
            channel.stats.subscription_count_month
        data['subscription_count'] = channel.stats.subscription_count
    try:
        data['average_rating'] = channel.rating.average
        data['count_rating'] = channel.rating.count
    except ObjectDoesNotExist:
        pass
    if hasattr(channel, 'score'):
        data['score'] = channel.score
    if hasattr(channel, 'guessed'):
        data['guessed'] = channel.guessed
        data['reasons'] = map(data_for_channel, channel.reasons)
    return data

def data_for_item(item):
    default_keys = ('name', 'description', 'url', 'size')
    data = {}
    for key in default_keys:
        data[key] = getattr(item, key)
    data['playback_url'] = util.make_absolute_url(item.get_url())
    if item.date is not None:
        data['date'] = item.date.isoformat()
    if item.thumbnail_exists():
        data['thumbnail_url'] = item.thumb_url(200, 133)
    return data

def error_response(request, error, text, code=None):
    data = {'error': error, 'text': text}
    if not code:
        code = 404
    return response_for_data(request, data, code)

def response_for_data(request, data, code=None):
    datatype = request.REQUEST.get('datatype', 'python')
    if datatype == 'python':
        contentType = 'text/x-python'
        stringData = repr(data)
    elif datatype == 'json':
        contentType = 'text/javascript'
        stringData = simplejson.dumps(data)
        if 'jsoncallback' in request.REQUEST:
            stringData = '%s(%s);' % (request.REQUEST['jsoncallback'],
                                      stringData)
    else:
        raise Http404
    response = HttpResponse(stringData,
                            content_type=contentType)
    if code:
        response.status_code = code
    return response

def test(request):
    data = {'text': 'Valid request' }
    return response_for_data(request, data)

@api_cache
def get_channel(request):
    if not ('id' in request.GET or 'url' in request.GET):
        return error_response(request, 'MISSING_ARGUMENT',
                              "get_channel requires either an id or a URL")
    channels = []
    for value in request.GET.getlist('id'):
        try:
            channels.append(api_utils.get_channel(
                                                  int(value)))
        except (LookupError, ValueError):
            return error_response(request, 'CHANNEL_NOT_FOUND',
                                  'Channel %s not found' % value)
    for value in request.GET.getlist('url'):
        try:
            channels.append(api_utils.get_channel_by_url(
                                                         value))
        except LookupError:
            return error_response(request, 'CHANNEL_NOT_FOUND',
                                  'Channel %s not found' % value)
    if request.user.is_authenticated():
        for channel in channels:
            channel.score = api_utils.get_rating(
                                                 request.user,
                                                 channel)
    if len(channels) == 1:
        data = data_for_channel(channels[0])
    else:
        data = map(data_for_channel, channels)
    return response_for_data(request, data)

@api_cache
@requires_arguments('filter', 'filter_value')
def get_channels(request):
    filter = request.GET['filter']
    value = request.GET['filter_value']
    sort = request.GET.get('sort')
    limit = request.GET.get('limit')
    if limit is not None:
        limit = int(limit)
    offset = request.GET.get('offset')
    if offset is not None:
        offset = int(offset)
    try:
        channels = api_utils.get_channels(request, filter, value, sort,
                                          limit, offset)
    except ValueError:
        raise Http404
    data = map(data_for_channel, channels)
    return response_for_data(request, data)

def get_session(request):
    engine = import_module(settings.SESSION_ENGINE)
    key = engine.SessionStore(None).session_key
    return response_for_data(request, {'session': key})

@login_required
def authenticate(request):
    redirectURL = request.REQUEST.get('redirect')
    sessionID = request.REQUEST.get('session')
    verification = sha.new(settings.SECRET_KEY +
                           str(redirectURL) + str(sessionID)).hexdigest()
    context = {
        'redirect': redirectURL,
        'session': sessionID,
        'verification': verification
    }
    if request.method == 'POST':
        if request.POST.get('submit') == 'No':
            return util.redirect('/')
        if request.POST.get('verification') == verification:
            engine = import_module(settings.SESSION_ENGINE)
            session = engine.SessionStore(sessionID)

            session['apiUser'] = request.user.id
            session.save()
            context['session'] = session.session_key
            if redirectURL:
                return util.redirect(redirectURL,
                                     {'session': session.session_key})
            else:
                context['success'] = True
        else:
            context['error'] = _("Invalid verification code.")
    return render_to_response('api/authenticate.html',
                              context,
                              context_instance=RequestContext(request))

@api_cache
@requires_login
@requires_arguments('id')
def rate(request):
    try:
        channel = api_utils.get_channel(
                                        int(request.GET.get('id')))
    except (LookupError, ValueError):
        return error_response(request, 'CHANNEL_NOT_FOUND',
                              'Channel %s not found' % request.GET.get('id'))
    if 'rating' in request.GET:
        api_utils.rate(request.user, channel, request.GET['rating'])
    return response_for_data(request,
                             {'rating':
                                  api_utils.get_rating(
                request.user, channel)})

@requires_login
def get_recommendations(request):
    start = int(request.GET.get('start', 0))
    length = int(request.GET.get('count', 50))
    channels = api_utils.get_recommendations(
                                             request.user, start, length)
    return response_for_data(request, map(data_for_channel,
                                          channels))

@api_cache
@requires_login
def get_ratings(request):
    rating = request.GET.get('rating')
    if rating is not None:
        ratings = api_utils.get_ratings(request.user,
                                  int(rating))
        return response_for_data(request, map(data_for_channel,
                                              ratings))
    else:
        ratings = api_utils.get_ratings(request.user)
        channels = ratings.keys()
        data = map(data_for_channel, channels)
        for index, channels in izip(count(), channels):
            data[index]['rating'] = ratings[channels]
        return response_for_data(request, data)

@api_cache
def list_labels(request, type):
    labels = api_utils.list_labels(type)
    data = [
        {'name': label.name,
         'url': label.get_absolute_url()}
        for label in labels]
    return response_for_data(request, data)
