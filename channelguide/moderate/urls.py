# Copyright (c) 2008-2009 Participatory Culture Foundation
# See LICENSE for details.

from django.conf.urls.defaults import patterns

urlpatterns = patterns('channelguide.moderate.views',
        (r'^$', 'index'),
        (r'^shared$', 'shared'),
        (r'^history$', 'history'),
        (r'^stats$', 'stats'),
        (r'^([\w-]+)/?$', 'channel_list'))

