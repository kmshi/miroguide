# Copyright (c) 2008-2009 Participatory Culture Foundation
# See LICENSE for details.

from django.conf import settings
from django.conf.urls.defaults import patterns, include, handler404
from django.views.generic.simple import direct_to_template, redirect_to

from django.contrib import admin
admin.autodiscover()

urlpatterns = patterns('channelguide.guide.views',
    (r'^$', 'frontpage.index'),
    (r'^admin/(.*)$', admin.site.root),
    (r'^favicon.ico$', redirect_to, {'url': '/images/favicon.ico'}),
    (r'^frontpage$', 'frontpage.index'),
    (r'^audio/', include('channelguide.guide.audio_urlconf')),
    (r'^firsttime$', 'firsttime.index'),
    (r'^accounts/', include('channelguide.user_profile.urls')),
    (r'^accounts/', include('django.contrib.auth.urls')),
    (r'^languages/', include('channelguide.labels.languages.urls')),
    (r'^notes/', include('channelguide.notes.urls')),
    (r'^watch/', include('channelguide.cobranding.urls')),
    (r'^i18n/setlang/?', 'i18n.set_language'),
    (r'^api/', include('channelguide.api.urls')),
    (r'^recommend/', include('channelguide.recommendations.urls')),
    (r'^ping/', include('channelguide.watched.urls')),
    (r'^submit/?', include('channelguide.submit.urls')),
    (r'^share/', include('channelguide.sharing.urls')),
    (r'^genres/', include('channelguide.labels.categories.urls')),
    (r'^tags/', include('channelguide.labels.tags.urls')),
    (r'^dmca$', direct_to_template,
     {'template': 'guide/dmca.html'}))

urlpatterns += patterns('channelguide.moderate.views',
    (r'^moderate$', 'index'),
    (r'^how-to-moderate$', 'how_to_moderate'),
    (r'^moderate/', include('channelguide.moderate.urls')))

urlpatterns += patterns('channelguide.search.views',
    (r'^search$', 'search'),
    (r'^search-more-channels$', redirect_to, {'url': '/search'}),
    (r'^search-more-items$', redirect_to, {'url': '/search'}))

urlpatterns += patterns('channelguide.user_profile.views',
    (r'^user/(.*)$', 'for_user'))

# new channel pages
urlpatterns += patterns('channelguide.channels.views',
                        (r'^popular/?$', 'filtered_listing', {
                    'filter': 'name',
                    'default_sort': '-popular',
                    'title': 'Popular Shows'}),
                        (r'^toprated/?$', 'filtered_listing', {
                    'filter': 'name',
                    'default_sort': '-rating',
                    'title': 'Top-Rated Shows'}),
                        (r'^feeds/?$', 'filtered_listing', {
                    'filter': 'feed',
                    'value': True,
                    'title': 'Feeds'}),
                        (r'^sites/?$', 'filtered_listing', {
                     'filter': 'feed',
                     'value':  False,
                     'title': 'Sites'}),
                        (r'^new/?$', 'filtered_listing', {
                    'filter': 'name',
                    'default_sort': '-age',
                    'title': 'New Shows'}),
                        (r'^featured/?$', 'filtered_listing', {
                    'filter': 'featured',
                    'value': True,
                    'title': 'Featured Shows'}),
                        (r'^hd/?$', 'filtered_listing', {
                    'filter': 'hd',
                    'value': True,
                    'title': 'High-Definition Shows'}),
                        (r'^(feeds|sites)/', include('channelguide.channels.urls')),
                        )

urlpatterns += patterns('channelguide.channels.playback',
                        (r'^items/(\d+)/?$', 'item'))

# donation pages
def donate_render(request, template):
    context = {'request': request,
               'google_analytics_ua': settings.GOOGLE_ANALYTICS_UA,
               'BASE_URL': settings.BASE_URL,
               'BASE_URL_FULL': settings.BASE_URL_FULL,
               'PAYPAL_URL': 'https://www.paypal.com/cgi-bin/webscr?cmd=_donations&business=donate%40pculture%2eorg&item_name=Tax%20Deductible%20Donation%20to%20Miro&page_style=MiroStore&no_shipping=1&return=https%3a%2f%2fwww%2emiroguide%2ecom%2fdonate%2fthanks&no_note=1&tax=0&currency_code=USD&lc=US&bn=PP%2dDonationsBF&charset=UTF%2d8',
               'CC_URL': 'https://www.getmiro.com/about/donate/cc-guide.html',
              }
    return direct_to_template(request,
                              template=template,
                              extra_context = context)

def donate_thanks(request):
    response = donate_render(request, template='donate/thanks.html')
    if 'donate_donated' not in request.COOKIES:
        response.set_cookie('donate_donated', 'yes', max_age=60*60*24*30,
                            secure=settings.USE_SECURE_COOKIES or None)
    return response

urlpatterns += patterns('',
                        (r'^donate$', donate_render, {
    'template': 'donate/donate.html'}),
                        (r'^donate/special$', donate_render, {
    'template': 'donate/special.html'}),
                        (r'^donate/biz$', donate_render, {
    'template': 'donate/biz.html'}),
                        (r'^donate/thanks$', donate_thanks),
                        )

# RSS feeds
from channelguide.guide import feeds

urlpatterns += patterns('',
    (r'^rss/(?P<name>new|featured|popular|toprated)/?', redirect_to,
     {'url': 'http://feeds.feedburner.com/miroguide/%(name)s'}))

urlpatterns = urlpatterns + patterns('',
    (r'^(?:rss|feeds)(?:_real)?/(?P<url>.*)$', feeds.cached_feed,
        {'feed_dict':
            {   'new': feeds.NewChannelsFeed,
                'features': feeds.FeaturedChannelsFeed,
                'featured': feeds.FeaturedChannelsFeed,
                'popular': feeds.PopularChannelsFeed,
                'toprated': feeds.TopRatedChannelsFeed,
                'categories': feeds.CategoriesFeed,
                'tags': feeds.TagsFeed,
                'languages': feeds.LanguagesFeed,
                'search': feeds.SearchFeed,
                'recommend': feeds.RecommendationsFeed}
        }),
    # be backwards compatible even though we're using /feeds/* for something
    # else now
    (r'^feeds/(?P<name>(new|featured|popular|toprated|categories|tags|languages|search|recommend).*)$',
     redirect_to, {'url': '/rss/%(name)s'}),
    (r'^feeds/features/?$', redirect_to, {'url': '/rss/featured'}),
)

# backwards compatible URLs
urlpatterns += patterns('',
                        (r'^browse/$', redirect_to, {'url': None}),
                        (r'^category-peek-fragment$', redirect_to,
                         {'url': None}),
                        (r'^channels/', include('channelguide.channels.urls')),
                        (r'^categories/', include('channelguide.labels.categories.urls')),
                        (r'^cobranding/', include('channelguide.cobranding.urls')))

js_info_dict = {
    'packages': ('channelguide.guide',),
}

urlpatterns += patterns('',
    (r'^jsi18n/$', 'django.views.i18n.javascript_catalog', js_info_dict),
)


handler500 = 'channelguide.guide.views.errors.error_500'

if settings.DEBUG:
    import os
    static_patterns = []
    for dir in ('css', 'images', 'js', 'movies', 'swf'):
        static_patterns.append((r'^%s/(?P<path>.*)$' % dir, 
            'django.views.static.serve',
            {'document_root': os.path.join(settings.STATIC_DIR, dir)}))
    urlpatterns.extend(patterns ('', *static_patterns))
    urlpatterns += patterns('',
                            (r'^media/(?P<path>.*)$',
                             'django.views.static.serve',
                             {'document_root': settings.MEDIA_ROOT}))
