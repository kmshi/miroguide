import urllib, operator

from django.conf import settings
from django.utils.decorators import decorator_from_middleware

from channelguide import util, cache
from channelguide.cache.middleware import AggressiveCacheMiddleware
from channelguide.guide import tables
from channelguide.guide.models import Channel, Category, PCFBlogPost
from sqlhelper.orm.query import ResultHandler

class FrontpageCacheMiddleware(AggressiveCacheMiddleware):

    def __init__(self):
        AggressiveCacheMiddleware.__init__(self, adult_differs=True)

    def get_cache_key_tuple(self, request):
        return (AggressiveCacheMiddleware.get_cache_key_tuple(self, request) +
                (request.user.is_authenticated(),))

def get_popular_channels(request, count):
    result = Channel.get_channels(request.connection, request.user,
            sort="subscription_count_today", limit=7,
            joins=("rating", "subscriptions"))
    for r in result:
        r.star_width = r.rating.average * 20
    return result

def get_featured_channels(request):
    return Channel.get_channels(request.connection, request.user,
        sort="random", filter="featured", filter_value=True)

def get_new_channels(request, count):
    return Channel.get_channels(request.connection, request.user,
        sort="new", limit=count)

def get_new_posts(connection, count):
    query = PCFBlogPost.query().order_by('position')
    return query.limit(count).execute(connection)

def get_categories(connection):
    rows = list(Category.query().order_by('name').execute(connection))
    adult_category = Category('Adult')
    rows.append(adult_category)
    rows.sort(key=operator.attrgetter('name'))
    return rows

def get_category_channels(request, category):
    popular_channels = Channel.get_channels(request.connection, request.user,
        sort="subscription_count_month", filter="category",
        filter_value=category.id, limit=2)

    query = Channel.query_approved(user=request.user).join(
            "categories").limit(4-len(popular_channels))
    query.joins['categories'].where(id=category.id)
    if popular_channels:
        query.where(Channel.c.id.not_in(c.id for c in popular_channels))
    query.order_by('RAND()')
    random_channels = list(query.execute(request.connection))
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
@decorator_from_middleware(FrontpageCacheMiddleware)
def index(request):
    if not request.user.is_authenticated():
        request.add_notification('Rate', 'Now you can rate channels in Miro Guide &mdash; it only takes 15 seconds to <a href="/accounts/login">get started</a>.<img src="%simages/small-star.png" />' % settings.STATIC_BASE_URL)
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

@cache.aggresively_cache(adult_differs=True)
def category_peek_fragment(request):
    return util.render_to_response(request, 'category-peek.html', {
        'category_peek': make_category_peek(request),
    })

@cache.cache_page_externally_for(60 * 60 * 24)
def refresh(request):
    return util.render_to_response(request, 'refresh.html',
            {'BASE_URL_FULL': settings.BASE_URL_FULL })
