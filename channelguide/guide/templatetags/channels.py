from django.conf import settings
from django.template import Library
from channelguide.guide.models import Rating, GeneratedRatings
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

@register.inclusion_tag('guide/channel-in-popular-list.html', takes_context=True)
def show_channel_in_popular_list(context, channel):
    return {'channel': channel, 'BASE_URL': settings.BASE_URL,
            'request': context['request']}

@register.inclusion_tag('guide/channel-in-recommendation.html', takes_context=True)
def show_channel_in_recommendation(context, channel, first, last):
    return {'request': context['request'], 'channel': channel,
            'BASE_URL': settings.BASE_URL, 'first': first, 'last': last}

@register.inclusion_tag('guide/channel-mini.html', takes_context=True)
def show_channel_mini(context, channel, count):
    return {'channel': channel, 'count': count, 
            'BASE_URL': settings.BASE_URL,
            'request': context['request']
            }

@register.inclusion_tag('guide/channel-mini.html')
def show_channel_recommendation(channel):
    return { 'channel': channel }

@register.inclusion_tag('guide/item.html')
def show_item(item, open=True):
    return {'item': item}

@register.inclusion_tag('guide/rating.html', takes_context=True)
def show_rating_stars(context, channel):
    request = context['request']
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
            'referer': request.path
        }

@register.inclusion_tag('guide/rating-static.html', takes_context=True)
def show_rating_static(context, channel):
    query = GeneratedRatings.query()
    request = context['request']
    try:
        average = query.get(request.connection, channel.id).average
    except LookupError:
        average = 0
    return {
            'average': average,
            'width': '%i%%' % (average*20),
            }
