from django.conf.urls.defaults import *

urlpatterns = patterns('channelguide.guide.views.tags',
    (r'^$', 'index'),
    (r'^(\d+)', 'tag'),
)
