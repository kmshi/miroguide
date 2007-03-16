from django.conf import settings
from django.template import Library
register = Library()

@register.inclusion_tag('guide/channel-full.html', takes_context=True)
def show_channel_full(context, channel):
    return {'channel': channel, 'user': context['user'], 
            'BASE_URL': settings.BASE_URL}

@register.inclusion_tag('guide/moderate-actions.html')
def show_moderate_actions(channel):
    return {'channel': channel, 'BASE_URL': settings.BASE_URL}

@register.inclusion_tag('guide/feature.html')
def show_channel_feature(channel):
    return {'channel': channel}

@register.inclusion_tag('guide/channel-normal.html')
def show_channel_normal(channel):
    return {'channel': channel}

@register.inclusion_tag('guide/channel-in-list.html')
def show_channel_in_list(channel):
    return {'channel': channel}

@register.inclusion_tag('guide/channel-mini.html')
def show_channel_mini(channel, count):
    return {'channel': channel, 'count': count}

@register.inclusion_tag('guide/item.html')
def show_item(item):
    return {'item': item}
