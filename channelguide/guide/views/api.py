from django.http import HttpResponse, HttpResponseNotFound, HttpResponseForbidden
from channelguide.guide.models import ApiKey, User
from channelguide import util
from channelguide.guide import api, tables
from channelguide.guide.auth import admin_required

class HttpResponseBadRequest(HttpResponse):
    status_code = 400

def requires_api_key(func):
    def wrapper(request):
        if 'key' not in request.REQUEST:
            return HttpResponseBadRequest('You forgot to send your API key')
        select = tables.api_key.select(tables.api_key.c.active)
        select.wheres.append(tables.api_key.c.api_key==request.REQUEST['key'])
        result = select.execute(request.connection)
        if not result:
            return HttpResponseForbidden('Invalid API key')
        elif result[0][0] == 0:
            return HttpResponseForbidden('Disabled API key')
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
    response = HttpResponse(repr(data), content_type='text/x-python')
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
    id = request.GET.get('id')
    try:
        channel = api.get_channel(request.connection, id)
    except LookupError:
        return error_response(request, 'CHANNEL_NOT_FOUND',
                'Channel %s not found' % id)
    data = data_for_channel(channel)
    return response_for_data(request, data)
