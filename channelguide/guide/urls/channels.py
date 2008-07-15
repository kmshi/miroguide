# Copyright (c) 2008 Participatory Culture Foundation
# See LICENSE for details.

from django.conf.urls.defaults import patterns
from django.views.generic.simple import redirect_to

urlpatterns = patterns('channelguide.guide.views.channels',
    (r'^(\d+)$', 'channel'),
    (r'^(\d+)/edit/?', 'edit_channel'),
    (r'^submitted_thumbnails/(\d+)$', 'submitted_thumbnail'),
    (r'^rate/(\d+)$', 'rate'),
    (r'^moderator-list/([\w-]+)$', 'moderator_channel_list'),
    (r'^subscribe/(\d+)$', 'subscribe'),
    (r'^subscribe-hit/(\d+)$', 'subscribe_hit'),
    (r'^user/(\d+)$', 'for_user'),
    (r'^edit/(\d+)$', 'edit_channel'),
    (r'^email/(\d+)$', 'email'),
    (r'^moderator-history$', 'moderator_history'),
    (r'^email-owners$', 'email_owners'),
)

# old URLs
urlpatterns += patterns('',
                        (r'^popular$', redirect_to, {'url': '/popular/'}),
                        (r'^toprated$', redirect_to, {'url': '/toprated/'}),
                        (r'^by-name$', redirect_to, {'url': '/feeds/'}),
                        (r'^recent$', redirect_to, {'url': '/new/'}),
                        (r'^features$', redirect_to, {'url': '/featured/'}),
                        (r'^hd$', redirect_to, {'url': '/hd/'}),
                        (r'^submit$', redirect_to, {'url': '/submit'})
                        )

