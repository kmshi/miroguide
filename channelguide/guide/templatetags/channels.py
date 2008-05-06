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
            'can_edit': user.can_edit_channel(channel),
            'show_script': showScript,
            'STATIC_BASE_URL': settings.STATIC_BASE_URL}

@register.inclusion_tag('guide/edit-bar.html', takes_context=True)
def show_edit_bar(context, channel, showScript=True):
    return {'channel': channel, 'user': context['user'],
            'STATIC_BASE_URL': settings.STATIC_BASE_URL,
            'show_script': showScript}

@register.inclusion_tag('guide/moderate-actions.html', takes_context=True)
def show_moderate_actions(context, channel):
    return {'channel': channel, 'STATIC_BASE_URL': settings.STATIC_BASE_URL,
            'user': context['user']}

@register.inclusion_tag('guide/simple-moderate-actions.html',
        takes_context=True)
def show_simple_moderate_actions(context, channel):
    return {'channel': channel, 'STATIC_BASE_URL': settings.STATIC_BASE_URL,
            'user': context['user']}

@register.inclusion_tag('guide/channel-small.html', takes_context=True)
def channel_small(context, channel):
    return {'request': context['request'], 'channel': channel,
            'STATIC_BASE_URL': settings.STATIC_BASE_URL }

@register.inclusion_tag('guide/personalized-recommendation.html', takes_context=True)
def show_personalized_recommendation(context, channel):
    return {'channel': channel, 'STATIC_BASE_URL': settings.STATIC_BASE_URL,
            'request': context['request']}

@register.inclusion_tag('guide/channel-mini.html', takes_context=True)
def channel_mini(context, channel, count):
    return {'channel': channel, 'count': count, 
            'STATIC_BASE_URL': settings.STATIC_BASE_URL,
            'request': context['request']
            }

    return { 'channel': channel }

@register.inclusion_tag('guide/item.html')
def show_item(item, open=True):
    return {'item': item}
