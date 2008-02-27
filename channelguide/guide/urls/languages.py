# Copyright (c) 2008 Participatory Culture Foundation
# See LICENSE for details.

from django.conf.urls.defaults import *

urlpatterns = patterns('channelguide.guide.views.languages',
    (r'^$', 'index'),
    (r'^(\d+)$', 'view'),
    (r'^moderate$', 'moderate'),
    (r'^add$', 'add'),
    (r'^delete$', 'delete'),
    (r'^change_name$', 'change_name'),
)
