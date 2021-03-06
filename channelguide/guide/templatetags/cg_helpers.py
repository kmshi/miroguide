# Copyright (c) 2008-2009 Participatory Culture Foundation
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
    nonce = hash(os.stat(fullpath))
    return template.TextNode('%s%s?%i' % (settings.STATIC_BASE_URL,
                                          filename,
                                          nonce))

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
            request_path = ''
        if self.path == request_path:
            css_class = 'current-page'
        else:
            css_class = None
        if request_path.startswith('/audio') and self.relative_path:
            if not self.relative_path.startswith('/'):
                self.relative_path = 'audio/' + self.relative_path
        return util.make_link_attributes(self.relative_path, css_class)

@register.inclusion_tag('guide/show-all.html')
def showall(text, length, css_class=None):
    if len(text.split()) > length:
        show_all = True
    else:
        show_all = False
    return {'text': text,
            'length': length,
            'show_all': show_all,
            'css_class': css_class
            }

@register.tag(name='ifshowall')
def ifshowall(parser, token):
    body = parser.parse(('endifshowall',))
    parser.delete_first_token()
    tokens = token.split_contents()
    node = make_text_or_variable_node(parser, tokens[1])
    length = int(tokens[2])
    return IfShowAllNode(body, node, length)

class IfShowAllNode(template.Node):
    def __init__(self, body, node, length):
        self.body = body
        self.node = node
        self.length = length

    def render(self, context):
        text = self.node.render(context)
        if len(text.split()) <= self.length:
            return ''
        else:
            return self.body.render(context)

@register.tag(name='wrap_translation')
def wrap_translation(parser, token):
    body = parser.parse(('endwrap',))
    parser.delete_first_token()
    tokens = token.split_contents()
    length = int(tokens[1])
    return WrapTranslationNode(body, length)

class WrapTranslationNode(template.Node):
    def __init__(self, body, length):
        self.body = body
        self.length = length

    def render(self, context):
        rendered_body = self.body.render(context).strip()
        if len(rendered_body) > self.length:
            title = rendered_body;
            cropped = rendered_body[:(self.length-3)] + '...'
            return '<span title="%s">%s</span>' % (title, cropped)
        else:
            return '<span>%s</span>' % rendered_body

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

@register.inclusion_tag('guide/pager-old.html')
def show_pager(pager):
    return {'pager': pager}

@register.inclusion_tag('guide/view-select.html')
def show_view_select(view_select):
    return {'view_select': view_select}

@register.tag(name='twocolumns')
def do_twocolumns(parser, token):
    first_column = parser.parse(('splitcolumns',))
    parser.delete_first_token()
    second_column = parser.parse(('endtwocolumns',))
    parser.delete_first_token()
    return TwoColumnNode(first_column, second_column)

class TwoColumnNode(template.Node):
    def __init__(self, first_column, second_column):
        self.columns = (first_column, second_column)

    def render(self, context):
        return """
<ul class="two-column-list">
    <li class="column first-column">
        %s
    </li>
    <li class="column second-column">
        %s
    </li>
</ul>
<div class="clear"></div>""" % (self.columns[0].render(context),
        self.columns[1].render(context))

@register.tag(name='threecolumns')
def do_threecolumns(parser, token):
    first_column = parser.parse(('splitcolumns',))
    parser.delete_first_token()
    second_column = parser.parse(('splitcolumns',))
    parser.delete_first_token()
    third_column = parser.parse(('endthreecolumns',))
    parser.delete_first_token()
    return ThreeColumnNode(first_column, second_column, third_column)

class ThreeColumnNode(template.Node):
    def __init__(self, first_column, second_column, third_column):
        self.columns = (first_column, second_column, third_column)

    def render(self, context):
        output = []
        output.append('<ul class="three-column-list">')
        output.append('<li class="column first-column">')
        output.append(self.columns[0].render(context))
        output.append('</li><li class="column second-column">')
        output.append(self.columns[1].render(context))
        output.append('</li><li class="column third-column">')
        output.append(self.columns[2].render(context))
        output.append('</li></ul><div class="clear"></div>')
        return ''.join(output)

def parse_column_loop(parser, token, deliminator):
    tokens = token.split_contents()
    syntax_msg = "syntax is twocolumnloop with <varname> in <list> [rotated]"
    if tokens[1] != 'with' or tokens[3] != 'in':
        raise template.TemplateSyntaxError(syntax_msg)
    if len(tokens) == 6:
        if tokens[5] == 'rotated':
            rotated = True
        else:
            raise template.TemplateSyntaxError(syntax_msg)
    elif len(tokens) == 5:
        rotated = False
    else:
        raise template.TemplateSyntaxError(syntax_msg)
    item_name = tokens[2]
    list_name = tokens[4]
    nodelist = parser.parse((deliminator,))
    parser.delete_first_token()
    return nodelist, list_name, item_name, rotated

@register.tag(name='twocolumnloop')
def do_twocolumnloop(parser, token):
    columns = ['first-column', 'second-column']
    return ColumnLoopNode(columns, 'two-column-list',
            *parse_column_loop(parser, token, 'endtwocolumnloop'))

@register.tag(name='threecolumnloop')
def do_threecolumnloop(parser, token):
    columns = ['first-column', 'second-column', 'third-column']
    return ColumnLoopNode(columns, 'three-column-list',
            *parse_column_loop(parser, token, 'endthreecolumnloop'))

@register.tag(name='fourcolumnloop')
def do_fourcolumnloop(parser, token):
    columns = ['first-column', 'second-column', 'third-column',
            'fourth-column']
    return ColumnLoopNode(columns, 'four-column-list',
            *parse_column_loop(parser, token, 'endfourcolumnloop'))

class ColumnLoopNode(template.Node):
    def __init__(self, column_names, list_css_class, nodelist, list_name, 
            item_name, rotated):
        self.column_names = column_names
        self.list_css_class = list_css_class
        self.width = len(self.column_names)
        self.nodelist = nodelist
        self.list_name = list_name
        self.item_name = item_name
        self.rotated = rotated

    def rotate_grid(self, list):
        pad_out = self.width - (len(list) % self.width)
        if pad_out == self.width: 
            pad_out = 0
        list = list + [None] * pad_out
        source_col = 0
        source_rows = len(list) / self.width
        retval = []
        while len(retval) < len(list):
            retval.extend(list[source_col:len(list):source_rows])
            source_col += 1
        return retval
    def render(self, context):
        loop_over = template.resolve_variable(self.list_name, context)
        if not isinstance(loop_over, list):
            loop_over = list(loop_over)
        if self.rotated:
            loop_over = self.rotate_grid(loop_over)
        output = ['<ul class="%s">' % self.list_css_class]
        counter = itertools.count()
        for item in loop_over:
            i = counter.next()
            if item is None:
                continue
            context[self.item_name] = item
            css_class = "column %s" % self.column_names[i % self.width]
            if i < self.width:
                css_class += ' first-row'
            if i + self.width >= len(loop_over):
                css_class += ' last-row'
            output.append('<li class="%s">' % css_class)
            output.append(self.nodelist.render(context))
            output.append('</li>\n')
        output.append('</ul><div class="clear"></div>')
        return ''.join(output)
