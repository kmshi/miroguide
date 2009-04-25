# Copyright (c) 2009 Michael C. Urbanski
# See LICENSE for details.

from django.conf.urls.defaults import *
from channelguide.aether.views import *
# submission
urlpatterns = patterns (
    '',
    (r'^add/(\d+)$', add_channel_subscription),
    (r'^remove/(\d+)$', remove_channel_subscription),
    (r'^deltas/(\d+)/(\d+)/(\d+)$', get_user_deltas),
    (r'^queue/(\d+)$', queue_download),
    (r'^dequeue/(\d+)$', cancel_download),
)
