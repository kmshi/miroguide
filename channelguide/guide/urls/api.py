from django.conf.urls.defaults import *

urlpatterns = patterns('channelguide.guide.views.api',
                       (r'^manage$', 'manage'),
                       (r'^test$', 'test'),
                       (r'^get_channel$', 'get_channel'),
                       (r'^get_channels$', 'get_channels'),
                       (r'^rate$', 'rate')
                       )
