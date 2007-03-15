from django.conf.urls.defaults import *

urlpatterns = patterns('channelguide.accounts.views',
    (r'^login$', 'login_view'),
    (r'^logout$', 'logout_view'),
    (r'^create$', 'create_user'),
    (r'^search$', 'search'),
    (r'^moderators$', 'moderators'),
    (r'^after-create$', 'after_create'),
    (r'^user/(\d+)$', 'user'),
)
