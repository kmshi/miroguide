# Copyright (c) 2008 Participatory Culture Foundation
# See LICENSE for details.

from django.conf.urls.defaults import patterns
from django.views.generic.simple import redirect_to

urlpatterns = patterns('channelguide.guide.views.share',
    (r'^feed/?$', 'share_feed'),
    (r'^item/?$', 'share_item'),
)
