from django.conf.urls.defaults import *

urlpatterns = patterns('channelguide.guide.views.ping',
                       (r'^watched$', 'watched'))
