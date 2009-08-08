# Copyright (c) 2009 Michael C. Urbanski
# See LICENSE for details.

from django.conf.urls.defaults import *
from channelguide.aether.api import (
    aether_authenticate,
    add_channel_subscription,
    remove_channel_subscription,
    queue_download, cancel_download,
    get_user_deltas, register_client,
    api_unsubscribe
)

urlpatterns = patterns (
    '',
    (r'^subscribe/(\d+)$', add_channel_subscription),
    (r'^unsubscribe/(\d+)$', remove_channel_subscription),
    (r'^queue/(\d+)$', queue_download),
    (r'^dequeue/(\d+)$', cancel_download),
    (r'^api/auth/$', aether_authenticate),
    (r'^api/register/?', register_client),
    (r'^api/deltas/$', get_user_deltas),
    (r'^api/unsubscribe/$', api_unsubscribe),
)
