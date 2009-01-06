# Copyright (c) 2008 Participatory Culture Foundation
# See LICENSE for details.

from django import template
from channelguide.guide.models import Rating

register = template.Library()

def _get_rating_context(context, channel):
    request = context['request']
    if not hasattr(channel, 'rating'):
        channel.join('rating').execute(request.connection)
    try:
        rating = Rating.query(Rating.c.user_id==request.user.id,
            Rating.c.channel_id==channel.id).get(request.connection)
    except Exception:
        rating = Rating()
        rating.channel_id = channel.id
        rating.has_user_rating = False
        if channel.rating:
            rating.average_rating = channel.rating.average
        else:
            rating.average_rating = 0
    else:
        rating.has_user_rating = True
        if rating.rating is None:
            rating.rating = 0
    return {
            'rating': rating,
            'referer': request.path,
        }

@register.inclusion_tag('guide/rating.html', takes_context=True)
def show_rating_stars(context, channel):
    return _get_rating_context(context, channel)

@register.inclusion_tag('guide/rating.html', takes_context=True)
def show_small_rating_stars(context, channel):
    context = _get_rating_context(context, channel)
    context['small'] = 'small'
    return context
