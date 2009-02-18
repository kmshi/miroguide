import simplejson
from itertools import izip, count
import sha
import cgi
from django.conf import settings
from django.http import HttpResponse
from django.utils.translation import ugettext as _
from channelguide import util
from channelguide.guide import api
from channelguide.guide.auth import login_required
from channelguide import sessions

def requires_arguments(*arguments):
    def outer(func):
        def wrapper(request):
            for name in arguments:
                if name not in request.REQUEST:
                    return error_response(request, 'MISSING_ARGUMENT',
                                          'You forgot the "%s" argument'
                                          % name)
            return func(request)
        return wrapper
    return outer

def requires_login(func):
    def wrapper(request):
        error = error_response(request, 'INVALID_SESSION',
                               'Invalid session', 403)
        if 'session' not in request.REQUEST:
            return error
        session = sessions.util.get_session_from_key(request.connection,
                                                     request.REQUEST[
                'session'])
        data = session.get_data()
        if 'apiUser' not in data:
            return error
        session.update_expire_date()
        session.save(request.connection)
        request.user = api.login(request.connection,
                                 data['apiUser'])

        return func(request)
    return wrapper

def data_for_channel(channel):
    default_keys = ('id', 'name', 'description', 'url', 'website_url',
            'hi_def', 'publisher', 'postal_code')
    data = dict((key, getattr(channel, key)) for key in default_keys)
    if channel.thumbnail_exists():
        data['thumbnail_url'] = channel.thumb_url(370, 247)
    if hasattr(channel, 'language'):
        data['language'] = channel.language.name
    if hasattr(channel, 'categories'):
        category = []
        for cat in channel.categories:
            category.append(cat.name)
        data['category'] = tuple(category)
    if hasattr(channel, 'tags'):
        tag = []
        for t in channel.tags:
            tag.append(t.name)
        data['tag'] = tuple(tag)
    if hasattr(channel, 'items'):
        items = []
        for item in channel.items:
            items.append(data_for_item(item))
        data['item'] = tuple(items)
    if getattr(channel, 'stats', None):
        data['subscription_count_today'] = channel.stats.subscription_count_today
        data['subscription_count_month'] = channel.stats.subscription_count_month
        data['subscription_count'] = channel.stats.subscription_count_total
    if getattr(channel, 'rating', None):
        data['average_rating'] = channel.rating.average
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
    response = HttpResponse(stringData,
                            content_type=contentType)
    if code:
        response.status_code = code
    return response

def test(request):
    data = {'text': 'Valid request' }
    return response_for_data(request, data)

def get_channel(request):
    if not ('id' in request.GET or 'url' in request.GET):
        return error_response(request, 'MISSING_ARGUMENT',
                              "get_channel requires either an id or a URL")
    channels = []
    for key, value in cgi.parse_qsl(request.META['QUERY_STRING']):
        if key == 'id':
            try:
                channels.append(api.get_channel(request.connection,
                                                int(value)))
            except (LookupError, ValueError):
                return error_response(request, 'CHANNEL_NOT_FOUND',
                              'Channel %s not found' % value)
        elif key == 'url':
            try:
                channels.append(api.get_channel_by_url(request.connection,
                                                       value))
            except LookupError, e:
                return error_response(request, 'CHANNEL_NOT_FOUND',
                                      'Channel %s not found' % value)
    if request.user.is_authenticated():
        for channel in channels:
            channel.score = api.get_rating(request.connection,
                                           request.user,
                                           channel)
    if len(channels) == 1:
        data = data_for_channel(channels[0])
    else:
        data = map(data_for_channel, channels)
    return response_for_data(request, data)

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
    channels = api.get_channels(request, filter, value, sort,
            limit, offset)
    data = map(data_for_channel, channels)
    return response_for_data(request, data)

def get_session(request):
    key = sessions.util.make_new_session_key(request.connection)
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
            if not sessionID:
                sessionID = sessions.util.make_new_session_key(
                    request.connection)
            session = sessions.util.get_session_from_key(request.connection,
                                                          sessionID)
            data = session.get_data()
            data['apiUser'] = request.user.id
            session.session_key = sessionID
            session.set_data(data)
            session.save(request.connection)
            context['session'] = sessionID
            if redirectURL:
                return util.redirect(redirectURL, {'session': sessionID})
            else:
                context['success'] = True
        else:
            context['error'] = _("Invalid verification code.")
    return util.render_to_response(request, 'api_authenticate.html',
                                   context)
@requires_login
@requires_arguments('id')
def rate(request):
    try:
        channel = api.get_channel(request.connection, request.GET.get('id'))
    except LookupError:
        return error_response(request, 'CHANNEL_NOT_FOUND',
                              'Channel %s not found' % request.GET.get('id'))
    if 'rating' in request.GET:
        channel.rate(request.connection, request.user,
                     request.GET.get('rating'))
    return response_for_data(request,
                             {'rating': api.get_rating(request.connection,
                                                       request.user, channel)})

@requires_login
def get_recommendations(request):
    start = int(request.GET.get('start', 0))
    length = int(request.GET.get('count', 50))
    channels = api.get_recommendations(request.connection,
                                       request.user, start, length)
    return response_for_data(request, map(data_for_channel,
                                          channels))

@requires_login
def get_ratings(request):
    rating = request.GET.get('rating')
    if rating is not None:
        ratings = api.get_ratings(request.connection, request.user,
                                  int(rating))
        return response_for_data(request, map(data_for_channel,
                                              ratings))
    else:
        ratings = api.get_ratings(request.connection, request.user)
        channels = ratings.keys()
        data = map(data_for_channel, channels)
        for index, channels in izip(count(), channels):
            data[index]['rating'] = ratings[channels]
        return response_for_data(request, data)

def list_labels(request, type):
    labels = api.list_labels(request.connection, type)
    data = [
        {'name': label.name,
         'url': label.get_absolute_url()}
        for label in labels]
    return response_for_data(request, data)
