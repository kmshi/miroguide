# Copyright (c) 2008-2009 Participatory Culture Foundation
# See LICENSE for details.

from django.conf.urls.defaults import *
from channelguide.labels.views import *
from channelguide.labels.models import Category
from channelguide.channels.views import filtered_listing

urlpatterns = patterns('channelguide.labels.categories.views',
    (r'^$', 'index', {}, 'category-index'),
    (r'^moderate$', moderate, {'model': Category,
                               'header': 'Edit Genres',
                               'new_label': 'New Genre',
                               'template': 'labels/edit-categories.html'},
     'category-moderate'),
    (r'^add$', add, {'model': Category}, 'category-add'),
    (r'^delete$', delete, {'model': Category}, 'category-delete'),
    (r'^change_name$', change_name, {'model': Category}, 'category-change'),
    (r'^toggle_frontpage$', 'toggle_frontpage', {},
     'category-toggle-frontpage'),
    (r'^(.+)$', filtered_listing, {
    'filter': 'category',
    'title': 'Genre: %(value)s'})
)
