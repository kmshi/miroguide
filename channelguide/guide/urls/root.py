# Copyright (c) 2008 Participatory Culture Foundation
# See LICENSE for details.

from django.conf import settings
from django.conf.urls.defaults import *
from django.views.generic.simple import direct_to_template, redirect_to

def cg_include(module):
    return include('channelguide.guide.urls.%s' % module)

urlpatterns = patterns('channelguide.guide.views',
    (r'^$', 'frontpage.index'),
    (r'^frontpage$', 'frontpage.index'),
    (r'^firsttime$', 'firsttime.index'),
    (r'^browse/$', redirect_to, {'url': None}),
    (r'^category-peek-fragment$', redirect_to, {'url': None}),
    (r'^moderate$', 'moderator.index'),
    (r'^how-to-moderate$', 'moderator.how_to_moderate'),
    (r'^search$', 'search.search'),
    (r'^search-more-channels$', redirect_to, {'url': '/search'}),
    (r'^search-more-items$', redirect_to, {'url': '/search'}),
    (r'^accounts/', cg_include('accounts')),
    (r'^categories/', cg_include('categories')),
    (r'^channels/', cg_include('channels')),
    (r'^languages/', cg_include('languages')),
    (r'^moderate/', cg_include('moderate')),
    (r'^notes/', cg_include('notes')),
    (r'^tags/', cg_include('tags')),
    (r'^cobranding/', cg_include('cobranding')),
    (r'^watch/', cg_include('cobranding')),
    (r'^i18n/setlang/', 'i18n.set_language'),
    (r'^api/', cg_include('api')),
    (r'^recommend/', cg_include('recommend')),
    (r'^ping/', cg_include('ping')),
)

# new channel pages
urlpatterns += patterns('channelguide.guide.views.channels',
                        (r'^popular/?$', 'filtered_listing', {
                    'filter': 'name',
                    'default_sort': '-popular',
                    'title': 'Popular Channels'}),
                        (r'^toprated/?$', 'filtered_listing', {
                    'filter': 'name',
                    'default_sort': '-rating',
                    'title': 'Top-Rated Channels'}),
                        (r'^feeds/?$', 'filtered_listing', {
                    'filter': 'name',
                    'default_sort': 'name',
                    'title': 'Channels by Name'}),
                        (r'^new/?$', 'filtered_listing', {
                    'filter': 'name',
                    'default_sort': '-age',
                    'title': 'New Channels'}),
                        (r'^featured$', 'features'),
                        (r'^hd$', 'hd'),
                        )

# submission
urlpatterns += patterns('channelguide.guide.views.submit',
    (r'^submit$', 'submit_feed'),
    (r'^submit/streaming$', 'submit_streaming'),
    (r'^submit/step1$', 'submit_feed'),
    (r'^submit/step2$', 'submit_channel'),
    (r'^submit/after$', 'after_submit'),
)


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

urlpatterns = urlpatterns + patterns('',
    (r'^rss/(?P<url>.*)$', 'django.contrib.syndication.views.feed',
        {'feed_dict':
            {   'new': feeds.NewChannelsFeed,
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

handler500 = 'channelguide.guide.views.errors.error_500'
