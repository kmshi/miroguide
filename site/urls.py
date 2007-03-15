from django.conf.urls.defaults import *

urlpatterns = patterns('',
    (r'^$', 'channelguide.channels.views.index'),
    (r'^category-peek-fragment$', 'channelguide.channels.views.category_peek_fragment'),
    (r'^accounts/', include('channelguide.accounts.urls')),
    (r'^channels/', include('channelguide.channels.urls')),
    (r'^languages/', include('channelguide.languages.urls')),
    (r'^notes/', include('channelguide.notes.urls')),
    (r'^categories/$', 'channelguide.channels.views.all_categories'),
    (r'^tags/$', 'channelguide.channels.views.all_tags'),
    (r'^categories/(\d+)', 'channelguide.channels.views.category'),
    (r'^tags/(\d+)', 'channelguide.channels.views.tag'),
    (r'^moderate$', 'channelguide.channels.views.moderate'),
    (r'^search$', 'channelguide.channels.views.search'),
    (r'^search-more-channels$', 'channelguide.channels.views.search_more'),
)
