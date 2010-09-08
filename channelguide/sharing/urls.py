# Copyright (c) 2008-2009 Participatory Culture Foundation
# See LICENSE for details.

from django.conf.urls.defaults import patterns

urlpatterns = patterns('channelguide.sharing.views',
    (r'^feed/?$', 'share_feed'),
    (r'^item/?$', 'share_item'),
    (r'^email/?$', 'email'),
)
