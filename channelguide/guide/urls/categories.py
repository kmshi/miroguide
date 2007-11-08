from django.conf.urls.defaults import *

urlpatterns = patterns('channelguide.guide.views.categories',
    (r'^$', 'index'),
    (r'^moderate$', 'moderate'),
    (r'^add$', 'add'),
    (r'^delete$', 'delete'),
    (r'^change_name$', 'change_name'),
    (r'^(.+)', 'category'),
)
