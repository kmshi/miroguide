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
        new_context = template.context.Context(self.features)
        new_context['channel'] = channel
        new_context.update(context)
        return self.nodelist.render(
            template.context.Context(new_context,
                                     autoescape=context.autoescape))

@register.tag('channel')
def channel(parser, token):
    tokens = token.split_contents()
    print tokens
    if len(tokens) < 2:
        raise template.TemplateSyntaxError(
            'syntax is {% channel <channel> [description] [buttons] \
[featured] %}')
    features = {}
    for token in tokens[2:]:
        features[token] = True
    if 'featured' in features:
        features['buttons'] = features['description'] = True
    if 'tiny' in features:
        features['small'] = True
    return ChannelNode(template.Variable(tokens[1]), features)


@register.inclusion_tag('guide/button_block.html', takes_context=True)
def button_block(context, channel):
    new_context = {'STATIC_BASE_URL': settings.STATIC_BASE_URL}
    new_context['small'] = context.get('small', False)
    return new_context

@register.inclusion_tag('guide/button_large.html')
def button_large(channel):
    return {'STATIC_BASE_URL': settings.STATIC_BASE_URL}
