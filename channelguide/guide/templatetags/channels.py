# Copyright (c) 2008 Participatory Culture Foundation
# See LICENSE for details.

from django.conf import settings
from django import template

register = template.Library()

class ChannelNode(template.Node):
    def __init__(self, channelVariable, features):
        self.channelVariable = channelVariable
        self.features = features

    def render(self, context):
        channel = self.channelVariable.resolve(context)
        t = template.loader.get_template('guide/channel.html')
        self.nodelist = t.nodelist
        new_context = template.context.Context(self.features,
                                               autoescape=context.autoescape)
        new_context.update(context)
        new_context['channel'] = channel
        return self.nodelist.render(new_context)

@register.tag('channel')
def channel(parser, token):
    tokens = token.split_contents()
    if len(tokens) < 2:
        raise template.TemplateSyntaxError(
            'syntax is {% channel <channel> [description] [buttons] \
[featured] %}')
    features = {}
    for token in tokens[2:]:
        features[token] = True
    if 'featured' in features or 'search' in features:
        features['buttons'] = features['description'] = True
    if 'tiny' in features:
        features['small'] = True
    return ChannelNode(template.Variable(tokens[1]), features)


@register.inclusion_tag('guide/button_block.html', takes_context=True)
def button_block(context, channel):
    new_context = {'STATIC_BASE_URL': settings.STATIC_BASE_URL}
    new_context['small'] = context.get('small', False)
    new_context['channel'] = channel
    return new_context

@register.inclusion_tag('guide/button_large.html')
def button_large(channel):
    return {'STATIC_BASE_URL': settings.STATIC_BASE_URL,
            'channel': channel}

@register.inclusion_tag('guide/edit-bar.html', takes_context=True)
def edit_bar(context, channel, show_script=True):
    return {'channel': channel,
            'request': context['request'],
            'user': context['request'].user,
            'show_script': show_script,
            'STATIC_BASE_URL': settings.STATIC_BASE_URL}

@register.inclusion_tag('guide/moderate-actions-simple.html',
                        takes_context=True)
def moderate_actions_simple(context, channel):
    return {'channel': channel,
            'user': context['request'].user}
