import urllib, operator

from django.conf import settings
from django.utils.decorators import decorator_from_middleware

from channelguide import util, cache
from channelguide.cache.middleware import AggressiveCacheMiddleware
from channelguide.guide import tables
from channelguide.guide.models import Channel, Category, PCFBlogPost
from sqlhelper.orm.query import ResultHandler

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

def get_popular_channels(request, count):
    query = Channel.query_approved(user=request.user)
    query.join('rating')
    query.load('subscription_count_today')
    query.order_by('subscription_count_today', desc=True)
    query.join('categories')
    query.limit(count*30)
    query.cacheable = cache.client
    query.cacheable_time = 300
    result = query.execute(request.connection)
    for r in result:
        r.star_width = r.rating.average * 20
    return _filter_categories(result, count)

def get_featured_channels(request):
    query = Channel.query_approved(featured=1, user=request.user)
    return query.order_by('RAND()').execute(request.connection)

def get_new_channels(request, count):
    query = Channel.query_new(user=request.user).load(
            'item_count').limit(count*3)
    query.join('categories')
#    query.cacheable = cache.client
#    query.cacheable_time = 3600
    return _filter_categories(query.execute(request.connection), count)

def get_new_posts(connection, count):
    query = PCFBlogPost.query().order_by('position')
    return query.limit(count).execute(connection)

def get_categories(connection):
    return Category.query(on_frontpage=True).order_by('name').execute(connection)

def get_category_channels(request, category):
    category.join('channels').execute(request.connection)
    query = Channel.query_approved(user=request.user).join("categories")
    query.where(Channel.c.id.in_(c.id for c in category.channels))
    query.load('subscription_count_month')
    query.order_by('subscription_count_month', desc=True)
    query.limit(6)
#    query.cacheable = cache.client
#    query.cacheable_time = 300
    popular_channels = []
    for channel in _filter_categories(query.execute(
        request.connection), 2):
        popular_channels.append(channel)
        yield channel

    query = Channel.query_approved(user=request.user)
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


@cache.cache_page_externally_for(300)
@cache.aggresively_cache
def index(request):
    featured_channels = get_featured_channels(request)
    return util.render_to_response(request, 'frontpage.html', {
        'popular_channels': get_popular_channels(request, 7),
        'new_channels': get_new_channels(request, 7),
        'featured_channels': featured_channels[:2],
        'featured_channels_hidden': featured_channels[2:],
        'blog_posts': get_new_posts(request.connection, 3),
        'categories': get_categories(request.connection),
        'category_peek': make_category_peek(request),
    })

@cache.aggresively_cache
def category_peek_fragment(request):
    return util.render_to_response(request, 'category-peek.html', {
        'category_peek': make_category_peek(request),
    })

@cache.cache_page_externally_for(60 * 60 * 24)
def refresh(request):
    return util.render_to_response(request, 'refresh.html',
            {'BASE_URL_FULL': settings.BASE_URL_FULL })
