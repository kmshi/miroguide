# Copyright (c) 2008 Participatory Culture Foundation
# See LICENSE for details.

import itertools, os

from django import template
from django.conf import settings
from channelguide import util

def quoted_attribute(attr):
    try:
        return attr[0] == attr[-1] == '"'
    except IndexError:
        return False

def unquote_attribute(attr):
    return attr[1:-1]

def make_text_or_variable_node(parser, expression):
    if quoted_attribute(expression):
        return template.TextNode(unquote_attribute(expression))
    else:
        return template.VariableNode(parser.compile_filter(expression))

register = template.Library()

@register.tag('static_nonce')
def do_static_nonce(parser, token):
    tokens = token.split_contents()
    if len(tokens) > 2 or not quoted_attribute(tokens[1]):
        raise template.TemplateSyntaxError(
            'syntax is {% static_nonce "<file_name>" %}')
    filename = unquote_attribute(tokens[1])
    fullpath = os.path.join(settings.STATIC_DIR, filename)
    if not os.path.exists(fullpath):
        raise template.TemplateSyntaxError('%s does not exist' % filename)
    return template.TextNode('?%i' % hash(os.stat(fullpath)))

@register.tag('link')
def do_link(parser, token):
    tokens = token.split_contents()
    syntax_msg = 'syntax is link <relative_link> ["css-class"]'
    if len(tokens) not in (2, 3):
        raise template.TemplateSyntaxError(syntax_msg)
    relative_link = tokens[1]
    try:
        css_class = tokens[2]
        if not quoted_attribute(css_class):
            raise template.TemplateSyntaxError(syntax_msg)
        css_class = unquote_attribute(css_class)
    except IndexError:
        css_class = None

    url_node = make_text_or_variable_node(parser, relative_link)
    return LinkNode(url_node, css_class)

class LinkNode(template.Node):
    def __init__(self, url_node, css_class):
        self.url_node = url_node
        self.css_class = css_class

    def render(self, context):
        relative_url = self.url_node.render(context)
        return util.make_link_attributes(relative_url, self.css_class)

@register.tag('navlink')
def do_navlink(parser, token):
    tokens = token.split_contents()
    if len(tokens) != 2 or not quoted_attribute(tokens[1]):
        msg = 'syntax is navlink "<relative_link_path>"'
        raise template.TemplateSyntaxError(msg)
    return NavLinkNode(unquote_attribute(tokens[1]))

class NavLinkNode(template.Node):
    def __init__(self, relative_path):
        self.path = settings.BASE_URL_PATH + relative_path
        self.relative_path = relative_path

    def render(self, context):
        try:
            request_path = context['request'].path
        except KeyError:
            request_path = None
        if self.path == request_path:
            css_class = 'current-page'
        else:
            css_class = None
        return util.make_link_attributes(self.relative_path, css_class)

@register.inclusion_tag('guide/account-bar.html', takes_context=True)
def show_account_bar(context, user):
    return {'user': user, 'LANGUAGES': settings.LANGUAGES,
            'request': context['request']}

@register.inclusion_tag('guide/form.html')
def show_form(form):
    return {'form': form, 'BASE_URL': settings.BASE_URL,
            'STATIC_BASE_URL': settings.STATIC_BASE_URL}

@register.inclusion_tag('guide/form-errors.html')
def show_form_errors(form):
    return {'form': form }

@register.inclusion_tag('guide/form-field.html')
def show_form_field(field):
    return {'field': field, 'BASE_URL': settings.BASE_URL,
            'STATIC_BASE_URL': settings.STATIC_BASE_URL}

@register.inclusion_tag('guide/formbutton.html')
def formbutton(url, action, label=None):
    if label is None:
        label = action
    return {'url': url, 'action': action, 'label': label}

@register.inclusion_tag('guide/pager.html')
def show_pager(pager):
    return {'pager': pager}

@register.inclusion_tag('guide/view-select.html')
def show_view_select(view_select):
    return {'view_select': view_select}
