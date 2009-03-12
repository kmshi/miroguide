# Copyright (c) 2008-2009 Participatory Culture Foundation
# See LICENSE for details.

from django.conf.urls.defaults import *

urlpatterns = patterns('channelguide.guide.views.moderator',
        (r'^$', 'index'),
        (r'^shared$', 'shared'),
        (r'^stats$', 'stats'),
        (r'^([\w-]+)/?$', 'channel_list'))

