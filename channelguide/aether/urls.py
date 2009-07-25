# Copyright (c) 2009 Michael C. Urbanski
# See LICENSE for details.

from django.conf.urls.defaults import *
from channelguide.aether.api import (
    aether_authenticate,
    add_channel_subscription,
    remove_channel_subscription,
    queue_download, cancel_download,
    get_user_deltas, register_client
)

urlpatterns = patterns (
    '',
    (r'^auth/$', aether_authenticate),
    (r'^subscribe/(\d+)$', add_channel_subscription),
    (r'^unsubscribe/(\d+)$', remove_channel_subscription),
    (r'^queue/(\d+)$', queue_download),
    (r'^dequeue/(\d+)$', cancel_download),
    (r'^register/?', register_client),
    (r'^deltas/([a-f0-9]{32})$', get_user_deltas),
)
