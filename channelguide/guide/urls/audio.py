# Copyright (c) 2008-2009 Participatory Culture Foundation
# See LICENSE for details.

from django.conf.urls.defaults import *

urlpatterns = patterns('channelguide.guide.views',
    (r'^$', 'frontpage.audio_index'),
    (r'^genres/$', 'categories.index'),
    (r'^languages/$', 'languages.index'),
    (r'^(\d+)$', 'channels.channel'),
    (r'^(\d+)/edit/?$', 'channels.edit_channel'),
    (r'^(\d+)/rate/?$', 'channels.rate'),
    (r'^(\d+)/latest/?$', 'channels.latest'),
    (r'^(\d+)/subscribe-hit/?$', 'channels.subscribe_hit'),
    (r'^(\d+)/add/?$', 'channels.user_add'),
    (r'^(\d+)/flag/?$', 'channels.flag'),
    (r'^(\d+)/email/?$', 'channels.email'),
    (r'^search$', 'search.search'))#, {'audio': True}))

# new channel pages
urlpatterns += patterns('channelguide.guide.views.channels',
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
