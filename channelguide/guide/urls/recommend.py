from django.conf.urls.defaults import *

urlpatterns = patterns('channelguide.guide.views.recommend',
    (r'^$', 'index'),
    (r'^ratings$', 'ratings'),
)
