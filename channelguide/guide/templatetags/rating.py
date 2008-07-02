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

@register.inclusion_tag('guide/rating.html', takes_context=True)
def rating(context, channel):
    request = context['request']
    user_rating = False
    if not hasattr(channel, 'rating'):
        channel.join('rating').execute(request.connection)
    if not channel.rating:
        channel.rating = GeneratedRatings()
        channel.rating.channel_id = channel.id
        channel.rating.save(request.connection)
    try:
        rating = Rating.query(Rating.c.user_id==request.user.id,
                              Rating.c.channel_id==channel.id).get(request.connection)
    except Exception:
        rating = None
    else:
        user_rating = True
        if rating.rating is None:
            rating.rating = 0
    return {
        'rating': rating,
        'channel': channel,
        'class': (user_rating and 'userrating' or 'averagerating'),
        'referer': request.path,
        }
