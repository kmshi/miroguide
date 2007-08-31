from django.conf.urls.defaults import *

urlpatterns = patterns('channelguide.guide.views.channels',
    (r'^submitted_thumbnails/(\d+)$', 'submitted_thumbnail'),
    (r'^(\d+)$', 'channel'),
    (r'^rating/(\d+)/(\d+)$', 'rating'),
    (r'^popular$', 'popular'),
    (r'^by-name$', 'by_name'),
    (r'^features$', 'features'),
    (r'^recent$', 'recent'),
    (r'^hd$', 'hd'),
    (r'^moderator-list/([\w-]+)$', 'moderator_channel_list'),
    (r'^subscribe/(\d+)$', 'subscribe'),
    (r'^subscribe-hit/(\d+)$', 'subscribe_hit'),
    (r'^submit$', 'submit_feed'),
    (r'^submit/step1$', 'submit_feed'),
    (r'^submit/step2$', 'submit_channel'),
    (r'^submit/after$', 'after_submit'),
    (r'^user/(\d+)$', 'for_user'),
    (r'^edit/(\d+)$', 'edit_channel'),
    (r'^moderator-history$', 'moderator_history'),
    (r'^email-owners$', 'email_owners'),
)
