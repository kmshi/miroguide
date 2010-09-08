# Copyright (c) 2008 Participatory Culture Foundation
# See LICENSE for details.

from channelguide.guide import emailmessages
from models import ChannelNote

def get_note_info(channel, user):
    """Get info about the notes that a user should see.

    If user is a moderator, she will see all the notes.  If the user is
    the channel owner he will see all the notes.  Otherwise, the user won't
    see any notes.

    Returns a list of notes to display.
    """

    if user.has_perm('channels.change_channel') or channel.owner == user:
        return channel.notes.all()
    else:
        return []

def make_rejection_note(channel, user, reason):
    """Make a canned rejection note and add it to this channels note list.
    reason should be one of the following:

    'Broken' -- Feed doesn't work with Miro
    'Explict' -- Explicit content
    'Copyrighted' -- Copyright issues
    'No Media' -- Feed isn't a video feed, or doesn't have enough video.
    """

    if reason == 'Broken':
        message = emailmessages.BrokenChannelEmail(channel)
    elif reason == 'Copyrighted':
        message = emailmessages.CopyrightViolationEmail(channel)
    elif reason == 'Explicit':
        message = emailmessages.ExplicitContentEmail(channel)
    elif reason == 'No Media':
        message = emailmessages.NoVideoEmail(channel)
    else:
        raise ValueError("Unknown rejection reason: %s" % reason)
    return ChannelNote(user=user, title='', body=message.body,
                       channel=channel)
