# Copyright (c) 2008-2009 Participatory Culture Foundation
# See LICENSE for details.

from django import template
from channelguide.ratings.models import Rating, GeneratedRatings

register = template.Library()

def _get_rating_context(context, channel):
    user = context['user']
    rating = None
    if user.is_authenticated():
        try:
            rating = Rating.objects.filter(user=context['user'],
                                           channel=channel).get()
        except Rating.DoesNotExist:
            pass
        else:
            rating.has_user_rating = True
            if rating.rating is None:
                rating.rating = 0

    if rating is None:
        rating = Rating(channel=channel)
        rating.has_user_rating = False
        generatedratings, created = GeneratedRatings.objects.get_or_create(
            channel=channel)
        rating.average_rating = channel.rating.average

    return {
        'rating': rating,
        'referer': context['request'].path,
        }

@register.inclusion_tag('ratings/rating.html', takes_context=True)
def show_rating_stars(context, channel):
    return _get_rating_context(context, channel)

@register.inclusion_tag('ratings/rating.html', takes_context=True)
def show_small_rating_stars(context, channel):
    context = _get_rating_context(context, channel)
    context['small'] = 'small'
    return context
