# Copyright (c) 2008-2009 Participatory Culture Foundation
# See LICENSE for details.

from django.conf.urls.defaults import *
from channelguide.guide.views.channels import filtered_listing
urlpatterns = patterns('channelguide.guide.views.tags',
    (r'^$', 'index'),
    (r'^(.+)$', filtered_listing, {
    'filter': 'tag',
    'title': 'Tag: %(value)s'}),
)
