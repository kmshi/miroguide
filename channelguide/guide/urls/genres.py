# Copyright (c) 2008-2009 Participatory Culture Foundation
# See LICENSE for details.

from django.conf.urls.defaults import *
from channelguide.guide.views.channels import filtered_listing
urlpatterns = patterns('channelguide.guide.views.categories',
    (r'^$', 'index'),
    (r'^moderate$', 'moderate'),
    (r'^add$', 'add'),
    (r'^delete$', 'delete'),
    (r'^change_name$', 'change_name'),
    (r'^toggle_frontpage$', 'toggle_frontpage'),
    (r'^(.+)$', filtered_listing, {
    'filter': 'category',
    'title': 'Genre: %(value)s'})
)
