import simplejson
from itertools import izip, count
from django.http import HttpResponse, HttpResponseNotFound
from channelguide.guide.models import ApiKey, User
from channelguide import util
from channelguide.guide import api, tables
from channelguide.guide.auth import admin_required

def requires_api_key(func):
    def wrapper(request):
        if 'key' not in request.REQUEST:
            return error_response(request, 'API_KEY_MISSING',
                                  'You forgot to send your API key',
                                  400)
        select = tables.api_key.select(tables.api_key.c.active)
        select.wheres.append(tables.api_key.c.api_key==request.REQUEST['key'])
        result = select.execute(request.connection)
        if not result:
            return error_response(request, 'API_KEY_INVALID',
                                  'Invalid API key', 403)
        elif result[0][0] == 0:
            return error_response(request, 'API_KEY_DISABLED',
                                  'Disabled API key', 403)
        return func(request)
    return wrapper

def requires_arguments(*arguments):
    def outer(func):
        def wrapper(request):
            for name in arguments:
                if name not in request.REQUEST:
                    return HttpResponseBadRequest('You forgot the "%s" argument' % name)
            return func(request)
        return wrapper
    return outer

def requires_login(func):
    def wrapper(request):
        if 'username' not in request.REQUEST:
            return HttpResponseBadRequest('You forgot the "username" argument')
        if 'password' not in request.REQUEST:
            return HttpResponseBadRequest('You forgot the "password" argument')
        request.user = api.login(request.
                                 connection,
                                 request.REQUEST['username'],
                                 request.REQUEST['password'])
        if request.user is None:
            return error_response(request, 'INVALID_USER',
                                  'Invalid username or password', 403)
        return func(request)
    return wrapper
        
def data_for_channel(channel):
    default_keys = ('id', 'name', 'description', 'url', 'website_url',
            'hi_def', 'publisher', 'postal_code')
    data = dict((key, getattr(channel, key)) for key in default_keys)
    if channel.thumbnail_exists():
        data['thumbnail_url'] = channel.thumb_url(370, 247)
    if hasattr(channel, 'language'):
        language = [channel.language.name]
        if hasattr(channel, 'secondary_languages'):
            for lang in channel.secondary_languages:
                language.append(lang.name)
        data['language'] = tuple(language)
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

@admin_required
def manage(request):
    if request.method == 'GET':
        keys = ApiKey.query()
        keys.join('owner')
        keys.order_by(keys.joins['owner'].c.username)
        return util.render_to_response(request, 'api-key.html',
                {'keys': keys.execute(request.connection)})
    else:
        action = request.POST['action']
        if action == 'add':
            owner = request.POST['owner']
            try:
                owner = User.query(username = owner).get(request.connection)
            except LookupError:
                return HttpResponseNotFound('invalid user name %s' % owner)
            description = request.POST['description']
            key = ApiKey.new(owner.id, description)
            key.save(request.connection)
            return util.redirect_to_referrer(request)
        elif action == 'toggle-active':
            key = request.POST['key']
            try:
                obj = ApiKey.get(request.connection, key)
            except:
                return HttpResponse('invalid key %s' % key)
            obj.active = not obj.active
            obj.save(request.connection)
            return util.redirect(request.path)

@requires_api_key
def test(request):
    data = {'text': 'Valid API key' }
    return response_for_data(request, data)

@requires_api_key
def get_channel(request):
    if not ('id' in request.GET or 'url' in request.GET):
        return HttpResponseBadRequest("get_channel requires either an id or a URL")
    if 'id' in request.GET:
        id = request.GET.get('id')
        try:
            channel = api.get_channel(request.connection, id)
        except LookupError:
            return error_response(request, 'CHANNEL_NOT_FOUND',
                              'Channel %s not found' % id)
    else:
        url = request.GET.get('url')
        try:
            channel = api.get_channel_by_url(request.connection, url)
        except LookupError:
            return error_response(request, 'CHANNEL_NOT_FOUND',
                                  'Channel %s not found' % url)
    data = data_for_channel(channel)
    return response_for_data(request, data)

@requires_api_key
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
    channels = api.get_channels(request.connection, filter, value, sort,
            limit, offset)
    data = map(data_for_channel, channels)
    return response_for_data(request, data)

@requires_api_key
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

@requires_api_key
@requires_login
def get_recommendations(request):
    start = int(request.GET.get('start', 0))
    count = int(request.GET.get('count', 50))
    channels = api.get_recommendations(request.connection,
                                       request.user, start, count)
    return response_for_data(request, map(data_for_channel,
                                          channels))

@requires_api_key
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
        
        
