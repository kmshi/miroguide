from django.conf.urls.defaults import *

urlpatterns = patterns('channelguide.guide.views.cobranding',
    (r'^admin/(.+)$', 'admin'),
    (r'^(.+)$', 'cobranding'))
