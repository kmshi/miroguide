from django.conf.urls.defaults import *

def cg_include(module):
    return include('channelguide.guide.urls.%s' % module)

urlpatterns = patterns('channelguide.guide.views',
    (r'^$', 'frontpage.index'),
    (r'^category-peek-fragment$', 'frontpage.peek_fragment'),
    (r'^moderate$', 'channels.moderate'),
    (r'^search$', 'channels.search'),
    (r'^search-more-channels$', 'channels.search_more'),
    (r'^accounts/', cg_include('accounts')),
    (r'^categories/', cg_include('categories')),
    (r'^channels/', cg_include('channels')),
    (r'^languages/', cg_include('languages')),
    (r'^notes/', cg_include('notes')),
    (r'^tags/', cg_include('tags')),
)
