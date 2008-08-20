# Copyright (c) 2008 Participatory Culture Foundation
# See LICENSE for details.

from django.conf import settings
from django.template import Library
from channelguide.guide.models import Rating, GeneratedRatings
register = Library()

@register.inclusion_tag('guide/channel-moderate.html', takes_context=True)
def show_channel_moderate(context, channel, showScript=True):
    user = context['user']
    return {'channel': channel, 'user': user,
            'request': context['request'],
            'can_edit': user.can_edit_channel(channel),
            'show_script': showScript,
            'STATIC_BASE_URL': settings.STATIC_BASE_URL}

@register.inclusion_tag('guide/edit-bar.html', takes_context=True)
def show_edit_bar(context, channel, showScript=True):
    request = context['request']
    if getattr(channel, 'featured_queue', None):
        channel.featured_queue.join('featured_by').execute(request.connection)
    return {'channel': channel, 'user': context['user'],
            'STATIC_BASE_URL': settings.STATIC_BASE_URL,
            'show_script': showScript}

@register.inclusion_tag('guide/moderate-actions.html', takes_context=True)
def show_moderate_actions(context, channel):
    return {'channel': channel, 'BASE_URL': settings.BASE_URL,
            'user': context['user']}

@register.inclusion_tag('guide/simple-moderate-actions.html',
        takes_context=True)
def show_simple_moderate_actions(context, channel):
    return {'channel': channel, 'STATIC_BASE_URL': settings.STATIC_BASE_URL,
            'user': context['user']}

@register.inclusion_tag('guide/channel-feature.html')
def show_channel_feature(channel):
    return {'channel': channel }

@register.inclusion_tag('guide/channel-feature-no-image.html')
def show_channel_feature_no_image(channel, position):
    return {'channel': channel, 'position': position}

@register.inclusion_tag('guide/channel-in-category.html')
def show_channel_in_category(channel):
    return {'channel': channel, 'STATIC_BASE_URL': settings.STATIC_BASE_URL }

@register.inclusion_tag('guide/channel-in-list.html')
def show_channel_in_list(channel):
    return {'channel': channel, 'STATIC_BASE_URL': settings.STATIC_BASE_URL }

@register.inclusion_tag('guide/channel-in-popular-list.html', takes_context=True)
def show_channel_in_popular_list(context, channel):
    return {'channel': channel, 'STATIC_BASE_URL': settings.STATIC_BASE_URL,
            'request': context['request']}

@register.inclusion_tag('guide/channel-in-recommendation.html', takes_context=True)
def show_channel_in_recommendation(context, channel, first, last):
    return {'request': context['request'], 'channel': channel,
            'STATIC_BASE_URL': settings.STATIC_BASE_URL,
            'first': first, 'last': last}

@register.inclusion_tag('guide/personalized-recommendation.html', takes_context=True)
def show_personalized_recommendation(context, channel):
    return {'channel': channel, 'STATIC_BASE_URL': settings.STATIC_BASE_URL,
            'request': context['request']}

@register.inclusion_tag('guide/channel-mini.html', takes_context=True)
def show_channel_mini(context, channel, count):
    return {'channel': channel, 'count': count, 
            'STATIC_BASE_URL': settings.STATIC_BASE_URL,
            'request': context['request']
            }

    return { 'channel': channel }

@register.inclusion_tag('guide/item.html')
def show_item(item, open=True):
    return {'item': item}

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
