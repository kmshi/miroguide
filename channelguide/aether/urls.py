# Copyright (c) 2009 Michael C. Urbanski
# See LICENSE for details.

from django.conf.urls.defaults import *
from channelguide.aether.views import *
from channelguide.aether.api import *

# submission
urlpatterns = patterns (
    '',
    (r'^add/(\d+)$', add_channel_subscription),
    (r'^remove/(\d+)$', remove_channel_subscription),
    (r'^queue/(\d+)$', queue_download),
    (r'^dequeue/(\d+)$', cancel_download),
    (r'^register/?', register_client),
    (r'^deltas/([a-f0-9]{32})$', get_user_deltas),
)
