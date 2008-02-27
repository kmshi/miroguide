# Copyright (c) 2008 Participatory Culture Foundation
# See LICENSE for details.

from django.conf.urls.defaults import *

urlpatterns = patterns('channelguide.guide.views.tags',
    (r'^$', 'index'),
    (r'^(\d+)', 'tag'),
)
