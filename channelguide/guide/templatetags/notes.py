from django import template
from django.conf import settings

register = template.Library()

@register.inclusion_tag('guide/note-list.html', takes_context=True)
def show_note_list(context, notes):
    return { 'notes': notes, 'BASE_URL': settings.BASE_URL }

@register.inclusion_tag('guide/post-list.html', takes_context=True)
def show_post_list(context, notes):
    return {'notes': notes, 'BASE_URL': settings.BASE_URL,
            'show_delete_buttons': context['user'].is_supermoderator()}

@register.inclusion_tag('guide/channel-notes.html', takes_context=True)
def show_channel_notes(context, notes):
    return { 'notes': notes, 'BASE_URL': settings.BASE_URL,
            'user': context['request'].user,
            'channel': context['channel'] }

@register.inclusion_tag('guide/add-note.html', takes_context=True)
def show_add_note(context, channel):
    return { 'channel': channel,
            'BASE_URL': settings.BASE_URL }
