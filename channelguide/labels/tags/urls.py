# Copyright (c) 2008-2009 Participatory Culture Foundation
# See LICENSE for details.

from django.conf.urls.defaults import *
from channelguide.labels.models import Tag
from channelguide.channels.views import filtered_listing

urlpatterns = patterns('channelguide.labels.views',
    (r'^$', 'index', {'model': Tag,
                      'paginator_count': 45,
                      'template': 'labels/tag-list.html'}, 'tag-index'),
    (r'^(.+)$', filtered_listing, {
    'filter': 'tag',
    'title': 'Tag: %(value)s'}),
)
