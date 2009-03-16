# Copyright (c) 2008-2009 Participatory Culture Foundation
# See LICENSE for details.

from django.conf.urls.defaults import *
from channelguide.guide.views.channels import filtered_listing

urlpatterns = patterns('channelguide.guide.views.languages',
    (r'^$', 'index'),
    (r'^moderate$', 'moderate'),
    (r'^add$', 'add'),
    (r'^delete$', 'delete'),
    (r'^change_name$', 'change_name'),
    (r'^(.+)$', filtered_listing, {
    'filter': 'language',
    'title': 'Language: %(value)s'})
)
