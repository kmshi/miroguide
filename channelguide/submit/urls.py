# Copyright (c) 2009 Participatory Culture Foundation
# See LICENSE for details.

from django.conf.urls.defaults import *

# submission
urlpatterns = patterns(
    'channelguide.submit.views',
    (r'^$', 'submit_feed'),
    (r'^step1$', 'submit_feed'),
    (r'^step2$', 'submit_channel'),
    (r'^after$', 'after_submit'),
    (r'^claim$', 'claim'),
)
