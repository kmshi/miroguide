# Copyright (c) 2008 Participatory Culture Foundation
# See LICENSE for details.

from django.conf.urls.defaults import patterns
from channelguide.guide.views.channels import filtered_listing

urlpatterns = patterns('channelguide.guide.views.channels',
    (r'^submitted_thumbnails/(\d+)$', 'submitted_thumbnail'),
    (r'^(\d+)$', 'channel'),
    (r'^rate/(\d+)$', 'rate'),
    (r'^popular(?:/?)$', filtered_listing, {
    'filter': 'name',
    'default_sort': '-popular',
    'title': 'Popular Channels'}),
                       (r'^toprated(?:/?)$', filtered_listing, {
    'filter': 'name',
    'default_sort': '-rating',
    'title': 'Top-Rated Channels'}),
                       (r'^by-name$', filtered_listing, {
    'filter': 'name',
    'title': 'Channels by Name'}),
                       (r'^new(?:/?)$', filtered_listing, {
    'filter': 'name',
    'default_sort': '-age',
    'title': 'New Channels'}),
    (r'^features$', 'features'),
    (r'^recent$', 'recent'),
    (r'^hd$', 'hd'),
    (r'^moderator-list/([\w-]+)$', 'moderator_channel_list'),
    (r'^subscribe/(\d+)$', 'subscribe'),
    (r'^subscribe-hit/(\d+)$', 'subscribe_hit'),
    (r'^user/(\d+)$', 'for_user'),
    (r'^edit/(\d+)$', 'edit_channel'),
    (r'^email/(\d+)$', 'email'),
    (r'^moderator-history$', 'moderator_history'),
    (r'^email-owners$', 'email_owners'),
)

urlpatterns += patterns('channelguide.guide.views.submit',
    (r'^submit$', 'submit_feed'),
    (r'^submit/streaming$', 'submit_streaming'),
    (r'^submit/step1$', 'submit_feed'),
    (r'^submit/step2$', 'submit_channel'),
    (r'^submit/after$', 'after_submit'),
)                        
