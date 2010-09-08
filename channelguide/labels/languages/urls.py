# Copyright (c) 2008-2009 Participatory Culture Foundation
# See LICENSE for details.

from django.conf.urls.defaults import *
from channelguide.labels.models import Language
from channelguide.channels.views import filtered_listing

urlpatterns = patterns('channelguide.labels.views',
    (r'^$', 'index', {'model': Language,
                      'group_name': 'Videos by Language'}, 'language-index'),
    (r'^moderate$', 'moderate', {'model': Language,
                                 'header': 'Edit Languages',
                                 'new_label': 'New Language'},
     'language-moderate'),
    (r'^add$', 'add', {'model': Language}, 'language-add'),
    (r'^delete$', 'delete', {'model': Language}, 'language-delete'),
    (r'^change_name$', 'change_name', {'model': Language},
     'language-change'),
    (r'^(.+)$', filtered_listing, {
    'filter': 'language',
    'title': 'Language: %(value)s'})
)
