from models import ChannelNote

def get_note_info(channel, user):
    """Get info about the notes that a user should see.  

    If user is a moderator, she will see all the notes.  If the user is
    the channel owner he will see only the notes with the type
    MODERATOR_TO_OWNER.  Otherwise, the user won't see any notes.  

    Returns a dictionary with the following keys:
       show_moderator_notes -- should the user see the moderator only notes?
       show_owner_notes -- ditto for moderator to user notes
       moderator_notes -- list of moderator only notes
       owner_notes -- list of moderator to user notes
    """

    info = {}
    if user.is_moderator():
        info['show_moderator_notes'] = True
        info['moderator_notes'] = [n for n in channel.notes \
                if n.type == ChannelNote.MODERATOR_ONLY]
    else:
        info['show_moderator_notes'] = False
        info['moderator_notes'] = []
    if user.is_moderator() or channel.owner is user:
        info['show_owner_notes'] = True
        info['owner_notes'] = [n for n in channel.notes \
                if n.type == ChannelNote.MODERATOR_TO_OWNER]
    else:
        info['show_owner_notes'] = False
        info['owner_notes'] = []
    return info
