# Copyright (c) 2008 Participatory Culture Foundation
# See LICENSE for details.

from django.conf import settings
from django import template
from channelguide.guide.models import Rating, GeneratedRatings
register = template.Library()

@register.tag
def rating_header(parser, tokens):
    return template.TextNode(
        """<script src="%sjs/rating.js" type="text/javascript"></script>
<link rel="StyleSheet" type="text/css" href="%scss/rating.css" />""" % (
        settings.STATIC_BASE_URL, settings.STATIC_BASE_URL))

def _setup_channel(channel, connection):
    if not hasattr(channel, 'rating'):
        channel.join('rating').execute(connection)
    if not channel.rating:
        channel.rating = GeneratedRatings()
        channel.rating.channel_id = channel.id
        channel.rating.save(connection)

def _rating_styles(rating):
    if not rating:
        return {'css_0': 'on'}
    else:
        context = {'css_1': 'on'}
        if rating > 1:
            context['css_2'] = 'on'
            if rating > 2:
                context['css_3'] = 'on'
                if rating > 3:
                    context['css_4'] = 'on'
                    if rating > 4:
                        context['css_5'] = 'on'
        return context
    
@register.inclusion_tag('guide/rating_stars.html', takes_context=True)
def rating(context, channel):
    request = context['request']
    _setup_channel(channel, request.connection)
    user_rating = False
    try:
        rating = Rating.query(Rating.c.user_id==request.user.id,
                              Rating.c.channel_id==channel.id).get(request.connection)
    except Exception:
        rating = None
    else:
        user_rating = True
        if rating.rating is None:
            rating.rating = 0
    context = {
        'rating': rating,
        'channel': channel,
        'class': (user_rating and 'userrating' or 'averagerating'),
        'referrer': request.get_full_path(),
        'BASE_URL': settings.BASE_URL,
        }
    if user_rating:
        context.update(_rating_styles(rating.rating))
    elif channel.rating.count:
        context.update(_rating_styles(channel.rating.average))
    return context

@register.inclusion_tag('guide/rating_meta.html', takes_context=True)
def rating_meta(context, channel):
    request = context['request']
    _setup_channel(channel, request.connection)
    return {'channel': channel}
