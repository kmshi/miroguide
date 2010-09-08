# Copyright (c) 2008-2009 Participatory Culture Foundation
# See LICENSE for details.

from django.conf.urls.defaults import patterns
from django.views.generic.simple import redirect_to

urlpatterns = patterns('channelguide.channels.views',
    (r'^(\d+)$', 'channel'),
    (r'^(\d+)/edit/?$', 'edit_channel'),
    (r'^(\d+)/latest/?$', 'latest'),
    (r'^(\d+)/add/?$', 'user_add'),
    (r'^(\d+)/email/?$', 'email'),
    (r'^subscriptions/?$', 'user_subscriptions'),
    (r'^email-owners$', 'email_owners'),
)

urlpatterns += patterns('channelguide.flags.views',
    (r'^(\d+)/flag/?$', 'flag'))


urlpatterns += patterns('channelguide.ratings.views',
    (r'^(\d+)/rate/?$', 'rate'))

urlpatterns += patterns('channelguide.subscriptions.views',
    (r'^(\d+)/subscribe-hit/?', 'subscribe_hit'))

# old URLs
urlpatterns += patterns('channelguide.channels.views',
                        (r'^popular$', redirect_to, {'url': '/popular/'}),
                        (r'^toprated$', redirect_to, {'url': '/toprated/'}),
                        (r'^by-name$', redirect_to, {'url': '/feeds/'}),
                        (r'^recent$', redirect_to, {'url': '/new/'}),
                        (r'^features$', redirect_to, {'url': '/featured/'}),
                        (r'^hd$', redirect_to, {'url': '/hd/'}),
                        (r'^submit$', redirect_to, {'url': '/submit'}),
                        (r'^moderator-list/(?P<name>[\w-]+)$', redirect_to,
                         {'url': '/moderate/%(name)s'}),
                        (r'^edit/(\d+)$', 'edit_channel'),
                        (r'^email/(\d+)$', 'email'),
                        )

