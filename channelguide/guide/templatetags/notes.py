from django import template
from django.conf import settings

register = template.Library()

@register.inclusion_tag('guide/channel-notes.html', takes_context=True)
def show_channel_notes(context, notes, channel):
    return { 'user': context['user'], 'notes': notes,  'channel': channel,
            'BASE_URL': settings.BASE_URL }

@register.inclusion_tag('guide/note-list.html', takes_context=True)
def show_note_list(context, notes):
    return { 'notes': notes, 'BASE_URL': settings.BASE_URL,
            'show_delete_buttons': context['user'].is_moderator() }

@register.inclusion_tag('guide/note-list.html', takes_context=True)
def show_post_list(context, notes):
    return { 'notes': notes, 'BASE_URL': settings.BASE_URL,
            'show_delete_buttons': context['user'].is_supermoderator() }

@register.inclusion_tag('guide/add-note.html', takes_context=True)
def show_add_note(context, type, channel):
    return { 'type': type, 'channel': channel,
            'show_email_checkbox': (type == 'moderator-to-owner' and
                context['user'].is_moderator()),
            'BASE_URL': settings.BASE_URL }
