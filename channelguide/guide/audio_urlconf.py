# Copyright (c) 2008-2009 Participatory Culture Foundation
# See LICENSE for details.

from django.conf.urls.defaults import *

from channelguide.labels.models import Language

urlpatterns = patterns('channelguide',
    (r'^$', 'guide.views.frontpage.audio_index'),
    (r'^genres/$', 'labels.categories.views.index'),
    (r'^languages/$', 'labels.views.index', {'model': Language,
                      'group_name': 'Audio Feeds by Language'},
     'language-index-audio'),
    (r'^(\d+)$', 'channels.views.channel'),
    (r'^(\d+)/edit/?$', 'channels.views.edit_channel'),
    (r'^(\d+)/rate/?$', 'ratings.views.rate'),
    (r'^(\d+)/latest/?$', 'channels.views.latest'),
    (r'^(\d+)/subscribe-hit/?$', 'subscriptions.views.subscribe_hit'),
    (r'^(\d+)/add/?$', 'channels.views.user_add'),
    (r'^(\d+)/flag/?$', 'flags.views.flag'),
    (r'^(\d+)/email/?$', 'channels.views.email'),
    (r'^search$', 'search.views.search'))#, {'audio': True}))

# new channel pages
urlpatterns += patterns('channelguide.channels.views',
                        (r'^popular/?$', 'filtered_listing', {
                    'filter': 'audio',
                    'value': True,
                    'default_sort': '-popular',
                    'title': 'Popular Podcasts'}),
                        (r'^toprated/?$', 'filtered_listing', {
                    'filter': 'audio',
                    'value': True,
                    'default_sort': '-rating',
                    'title': 'Top-Rated Podcasts'}),
                        (r'^new/?$', 'filtered_listing', {
                    'filter': 'audio',
                    'value': True,
                    'default_sort': '-age',
                    'title': 'New Podcasts'}),
                        (r'^featured/?$', 'filtered_listing', {
                    'filter': 'featured',
                    'value': True,
                    'title': 'Featured Podcasts'}),
                        (r'^genres/(.+)$', 'filtered_listing', {
            'filter': 'category',
            'title': 'Genre: %(value)s'}),
                        (r'^languages/(.+)$', 'filtered_listing', {
            'filter': 'language',
            'title': 'Language: %(value)s'})
                        )
