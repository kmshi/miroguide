from django.conf.urls.defaults import *

def cg_include(module):
    return include('channelguide.guide.urls.%s' % module)

urlpatterns = patterns('channelguide.guide.views',
    (r'^$', 'frontpage.refresh'),
    (r'^front$', 'frontpage.index'),
    (r'^category-peek-fragment$', 'frontpage.category_peek_fragment'),
    (r'^moderate$', 'moderator.index'),
    (r'^how-to-moderate$', 'moderator.how_to_moderate'),
    (r'^search$', 'search.search'),
    (r'^search-more-channels$', 'search.search_more'),
    (r'^search-more-items$', 'search.search_more_items'),
    (r'^accounts/', cg_include('accounts')),
    (r'^categories/', cg_include('categories')),
    (r'^channels/', cg_include('channels')),
    (r'^languages/', cg_include('languages')),
    (r'^notes/', cg_include('notes')),
    (r'^tags/', cg_include('tags')),
)

handler500 = 'channelguide.guide.views.errors.error_500'
