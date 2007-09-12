from django.conf.urls.defaults import *

urlpatterns = patterns('channelguide.guide.views.accounts',
    (r'^login$', 'login_view'),
    (r'^logout$', 'logout_view'),
    (r'^search$', 'search'),
    (r'^moderators$', 'moderators'),
    (r'^forgot-password$', 'forgot_password'),
    (r'^auth-token-sent$', 'auth_token_sent'),
    (r'^change-password$', 'change_password'),
    (r'^change-password/(\d+)$', 'change_password_submit'),
    (r'^password-changed$', 'password_changed'),
    (r'^confirm/(\d+)/([a-z0-9]+)', 'confirm'),
    (r'^(\d+)$', 'user'),
)
