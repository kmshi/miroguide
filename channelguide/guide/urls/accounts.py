from django.conf.urls.defaults import *

urlpatterns = patterns('channelguide.guide.views.accounts',
    (r'^login$', 'login_view'),
    (r'^logout$', 'logout_view'),
    (r'^search$', 'search'),
    (r'^moderators$', 'moderators'),
    (r'^moderator-board-emails/(\d+)$', 'moderator_board_emails'),
    (r'^status-emails/(\d+)$', 'status_emails'),
    (r'^(\d+)$', 'user'),
)
