from django.conf.urls.defaults import *

urlpatterns = patterns('channelguide.guide.views.moderator',
        (r'^$', 'index'),
        (r'^shared$', 'shared'))
