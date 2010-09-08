# Copyright (c) 2008 Participatory Culture Foundation
# See LICENSE for details.

from django import template
from django.conf import settings

register = template.Library()

@register.inclusion_tag('notes/note-list.html', takes_context=True)
def show_note_list(context, notes):
    return { 'notes': notes, 'BASE_URL': settings.BASE_URL }

@register.inclusion_tag('notes/post-list.html', takes_context=True)
def show_post_list(context, notes):
    return {'notes': notes, 'BASE_URL': settings.BASE_URL,
            'show_delete_buttons':
                context['user'].has_perm('notes.delete_moderatorpost')}

@register.inclusion_tag('notes/channel-notes.html', takes_context=True)
def show_channel_notes(context, notes):
    return { 'notes': notes, 'BASE_URL': settings.BASE_URL,
            'user': context['request'].user,
            'channel': context['channel'] }

@register.inclusion_tag('notes/add-note.html', takes_context=True)
def show_add_note(context, channel):
    return { 'channel': channel,
            'BASE_URL': settings.BASE_URL }
