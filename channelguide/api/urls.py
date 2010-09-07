# Copyright (c) 2009 Participatory Culture Foundation
# See LICENSE for details.

from django.conf.urls.defaults import *

urlpatterns = patterns('channelguide.api.views',
                       (r'^test$', 'test'),
                       (r'^get_channel$', 'get_channel'),
                       (r'^get_channels$', 'get_channels'),
                       (r'^get_feeds$', 'get_feeds'),
                       (r'^get_sites$', 'get_sites'),
                       (r'^get_session$', 'get_session'),
                       (r'^authenticate$', 'authenticate'),
                       (r'^rate$', 'rate'),
                       (r'^get_ratings$', 'get_ratings'),
                       (r'^get_recommendations$', 'get_recommendations'),
                       (r'^list_categories', 'list_labels',
                        {'type': 'category'}),
                       (r'^list_languages', 'list_labels',
                        {'type': 'language'})
                       )
