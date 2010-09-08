# Copyright (c) 2009 Participatory Culture Foundation
# See LICENSE for details.

from django.conf.urls.defaults import *

urlpatterns = patterns('channelguide.watched.views',
                       (r'^watched$', 'watched'))
