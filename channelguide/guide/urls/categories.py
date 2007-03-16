from django.conf.urls.defaults import *

urlpatterns = patterns('channelguide.guide.views.categories',
    (r'^$', 'index'),
    (r'^(\d+)', 'category'),
)
