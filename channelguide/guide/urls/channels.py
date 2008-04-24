# Copyright (c) 2008 Participatory Culture Foundation
# See LICENSE for details.

from django.conf.urls.defaults import *

urlpatterns = patterns('channelguide.guide.views.channels',
    (r'^submitted_thumbnails/(\d+)$', 'submitted_thumbnail'),
    (r'^(\d+)$', 'channel'),
    (r'^rate/(\d+)$', 'rate'),
    (r'^popular$', 'popular_view'),
    (r'^toprated$', 'toprated'),
    (r'^by-name$', 'by_name'),
    (r'^features$', 'features'),
    (r'^recent$', 'recent'),
    (r'^hd$', 'hd'),
    (r'^moderator-list/([\w-]+)$', 'moderator_channel_list'),
    (r'^subscribe/(\d+)$', 'subscribe'),
    (r'^subscribe-hit/(\d+)$', 'subscribe_hit'),
    (r'^user/(\d+)$', 'for_user'),
    (r'^edit/(\d+)$', 'edit_channel'),
    (r'^email/(\d+)$', 'email'),
    (r'^moderator-history$', 'moderator_history'),
    (r'^email-owners$', 'email_owners'),
)

urlpatterns += patterns('channelguide.guide.views.submit',
    (r'^submit$', 'submit_feed'),
    (r'^submit/streaming$', 'submit_streaming'),
    (r'^submit/step1$', 'submit_feed'),
    (r'^submit/step2$', 'submit_channel'),
    (r'^submit/after$', 'after_submit'),
)                        
