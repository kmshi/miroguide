import urllib

from sqlalchemy import desc, func

from channelguide import util, cache
from channelguide.db import dbutil
from channelguide.guide.models import Channel, Category, PCFBlogPost

def get_popular_channels(channel_query, count):
   select = channel_query.select_by(state=Channel.APPROVED)
   return select.order_by(desc(Channel.c.subscription_count))[:count]

def get_featured_channels(channel_query):
   select = channel_query.select_by(state=Channel.APPROVED, featured=1)
   return select.order_by(func.rand())

def get_new_channels(channel_query, count):
   select = channel_query.select_by(state=Channel.APPROVED)
   return select.order_by(desc(Channel.c.approved_at))[:count]

def get_category_channels(channel_query, category, count):
    select = channel_query.select_by(state='A')
    select = select.filter(channel_query.join_to('categories'))
    select = select.filter(Category.c.id == category.id)
    return dbutil.select_random(select, count)

# category peeks are windows into categories that show a few (6) channels.
def get_peeked_category(category_query, get_params):
    try:
        dir, name = get_params['category_peek'].split(':')
    except:
        return dbutil.select_random(category_query.select(), 1)[0]
    if dir == 'after':
        select = category_query.select(Category.c.name > name,
                order_by=Category.c.name)
    else:
        select = category_query.select(Category.c.name < name,
                order_by=desc(Category.c.name))
    try:
        return select[0]
    except IndexError:
        if dir == 'after':
            return category_query.select(order_by=Category.c.name)[0]
        else:
            return category_query.select(order_by=desc(Category.c.name))[0]

def make_category_peek(request):
    channel_query = request.db_session.query(Channel)
    category_query = request.db_session.query(Category)
    try:
        category = get_peeked_category(category_query, request.GET)
    except IndexError: # no categories defined
        return None
    name = urllib.quote_plus(category.name)
    return {
            'category': category,
            'channels': get_category_channels(channel_query, category, 6),
            'prev_url': '?category_peek=before:%s' % name,
            'next_url': '?category_peek=after:%s' % name,
            'prev_url_ajax': 'category-peek-fragment?category_peek=before:%s' % name,
            'next_url_ajax': 'category-peek-fragment?category_peek=after:%s' % name,
    }


@cache.cache_page_externally_for(300)
@cache.aggresively_cache
def index(request):
    channel_query = request.db_session.query(Channel)
    category_query = request.db_session.query(Category)
    post_query = request.db_session.query(PCFBlogPost,
            order_by=PCFBlogPost.c.position)
    featured_channels = get_featured_channels(channel_query).list()

    return util.render_to_response(request, 'frontpage.html', {
        'popular_channels': get_popular_channels(channel_query, 7),
        'new_channels': get_new_channels(channel_query, 7),
        'featured_channels': featured_channels[:2],
        'featured_channels_hidden': featured_channels[2:],
        'category_peek': make_category_peek(request),
        'blog_posts': post_query.select(limit=3),
        'categories': category_query.select(order_by=Category.c.name),
    })

def category_peek_fragment(request):
    return util.render_to_response(request, 'category-peek.html', {
        'category_peek': make_category_peek(request),
    })

def refresh(request):
    return util.render_to_response(request, 'refresh.html')
