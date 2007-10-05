from django.conf import settings
from django.template import Library
register = Library()

@register.inclusion_tag('guide/channel-full.html', takes_context=True)
def show_channel_full(context, channel):
    user = context['user']
    return {'channel': channel, 'user': user,
            'show_edit_button': user.can_edit_channel(channel),
            'show_extra_info': user.can_edit_channel(channel),
            'link_to_channel': True,
            'BASE_URL': settings.BASE_URL}

@register.inclusion_tag('guide/channel-full.html', takes_context=True)
def show_channel_full_no_link(context, channel):
    user = context['user']
    return {'channel': channel, 'user': user,
            'show_edit_button': user.can_edit_channel(channel),
            'show_extra_info': user.can_edit_channel(channel),
            'link_to_channel': False,
            'BASE_URL': settings.BASE_URL}

@register.inclusion_tag('guide/moderate-actions.html')
def show_moderate_actions(channel):
    return {'channel': channel, 'BASE_URL': settings.BASE_URL}

@register.inclusion_tag('guide/channel-feature.html')
def show_channel_feature(channel):
    return {'channel': channel }

@register.inclusion_tag('guide/channel-feature-no-image.html')
def show_channel_feature_no_image(channel, position):
    return {'channel': channel, 'position': position}

@register.inclusion_tag('guide/channel-in-category.html')
def show_channel_in_category(channel):
    return {'channel': channel, 'BASE_URL': settings.BASE_URL }

@register.inclusion_tag('guide/channel-in-list.html')
def show_channel_in_list(channel):
    return {'channel': channel, 'BASE_URL': settings.BASE_URL }

@register.inclusion_tag('guide/channel-in-popular-list.html')
def show_channel_in_popular_list(channel):
    return {'channel': channel, 'BASE_URL': settings.BASE_URL }

@register.inclusion_tag('guide/channel-in-recommendation.html')
def show_channel_in_recommendation(channel):
    return {'channel': channel, 'BASE_URL': settings.BASE_URL }

@register.inclusion_tag('guide/channel-mini.html')
def show_channel_mini(channel, count):
    return {'channel': channel, 'count': count, 
            'BASE_URL': settings.BASE_URL
            }

@register.inclusion_tag('guide/item.html')
def show_item(item):
    return {'item': item}
