from django.conf.urls.defaults import *

urlpatterns = patterns('channelguide.languages.views',
    (r'^$', 'index'),
    (r'^(\d+)$', 'view'),
    (r'^moderate$', 'moderate'),
    (r'^add$', 'add'),
    (r'^delete$', 'delete'),
    (r'^change_name$', 'change_name'),
)
