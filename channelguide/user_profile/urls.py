# Copyright (c) 2008-2009 Participatory Culture Foundation
# See LICENSE for details.

from django.conf.urls.defaults import patterns

urlpatterns = patterns('channelguide.user_profile.views',
    (r'^register/?$', 'register_view'),
    (r'^search$', 'search'),
    (r'^moderators$', 'moderators'),
    (r'^confirm/(\d+)/([a-z0-9]+)', 'confirm'),
    (r'^set_language_view$', 'set_language_view'),
    (r'^profile/?$', 'user'),
    (r'^profile/(\d+)/$', 'user'),
)

urlpatterns += patterns('django.contrib.auth.views',
    (r'logout/?$', 'logout', {'next_page': '/'}))
