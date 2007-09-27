import urllib

from django.conf import settings

from channelguide import util, cache
from channelguide.guide import tables, popular
from channelguide.guide.models import Channel, Category, PCFBlogPost
from sqlhelper.orm.query import ResultHandler
def get_popular_channels(connection, count):
    return popular.get_popular('today', connection, count)

def get_featured_channels(connection):
    query = Channel.query_approved(featured=1)
    return query.order_by('RAND()').execute(connection)

def get_new_channels(connection, count):
    query = Channel.query_approved().load('item_count')
    query.order_by('approved_at', desc=True).limit(count)
#    query.cacheable = cache.client
#    query.cacheable_time = 60
    return query.execute(connection)

def get_new_posts(connection, count):
    query = PCFBlogPost.query().order_by('position')
    return query.limit(count).execute(connection)

def get_categories(connection):
    return Category.query().order_by('name').execute(connection)

def get_category_channels(connection, category):
    query = Channel.query_approved().join("categories")
    query.joins['categories'].where(id=category.id)
    query.cacheable = cache.client
    query.cacheable_time = 300
    popular_channels = list(popular.get_popular('month', connection, limit=2,
            query=query))

    query = Channel.query_approved().join("categories").limit(2)
    query.joins['categories'].where(id=category.id)
    query.where(Channel.c.id.not_in(c.id for c in popular_channels))
    query.order_by('RAND()')
    random_channels = list(query.execute(connection))
    return popular_channels + random_channels

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
            'channels': get_category_channels(request.connection, category),
            'prev_url': '?category_peek=before:%s' % name,
            'next_url': '?category_peek=after:%s' % name,
            'prev_url_ajax': 'category-peek-fragment?category_peek=before:%s' % name,
            'next_url_ajax': 'category-peek-fragment?category_peek=after:%s' % name,
    }


    #@cache.aggresively_cache
#@cache.cache_page_externally_for(300)
def index(request):
    featured_channels = get_featured_channels(request.connection)
    return util.render_to_response(request, 'frontpage.html', {
        'popular_channels': get_popular_channels(request.connection, 7),
        'new_channels': get_new_channels(request.connection, 7),
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
