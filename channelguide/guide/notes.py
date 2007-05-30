import urllib

from django.conf import settings

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
    if user.is_moderator() or channel.owner_id == user.id:
        info['show_owner_notes'] = True
        info['owner_notes'] = [n for n in channel.notes \
                if n.type == ChannelNote.MODERATOR_TO_OWNER]
    else:
        info['show_owner_notes'] = False
        info['owner_notes'] = []
    return info

def rejection_header(text):
    text = ' %s ' % text
    left = '-' * ((50 - len(text)) / 2)
    right = '-' * ((51 - len(text)) / 2)
    return left + text + right

def make_rejection_note(channel, user, reason):
    """Make a canned rejection note and add it to this channels note list.
    reason should be one of the following:

    'Broken' -- Feed doesn't work with Miro
    'Explict' -- Explicit content
    'Copyright' -- Copyright issues
    'No Video' -- Feed isn't a video feed, or doesn't have enough video.
    """

    title = '%s was not approved' % channel.name
    paragraphs = []
    if reason == 'Broken':
        feedvalidator_link = 'http://feedvalidator.org/check.cgi?url='
        feedvalidator_link += urllib.quote_plus(channel.url)

        header = rejection_header('BROKEN')
        paragraphs.append("""\
Your feed doesn't seem to work in Democracy. Check it out in
feedvalidator.org (%s). If you're having problems finding the problem,
please search the democracy forums (%s) and post a question if you
don't find an answer.""" % (feedvalidator_link, settings.FORUMS_URL))
        paragraphs.append("""\
Once you have your feed working in Democracy, please post a message
for us on the channel page (%s).""" % channel.get_absolute_url())
    elif reason == 'Copyright':
        header = rejection_header('COPYRIGHT ISSUES')
        paragraphs.append("""\
It appears that your feed might have copyrighted material in it. Due to
the nature of US copyright laws, we cannot feature it in the Channel Guide.""")
        paragraphs.append("""\
If we are incorrect in supposing that the material was not cleared for
copyright, please contact us at channels@pculture.org""")
    elif reason == 'Explicit':
        header = rejection_header('EXPLICIT CONTENT')
        paragraphs.append("""\
Currently, we don't have an user controllable filtering system in place
and cannot accept feeds that are more than "R Rated".""")
    elif reason == 'No Video':
        header = rejection_header('NO VIDEO')
        paragraphs.append("""\
Your feed is missing video files (it is either empty or consists of
audio only). We require there to be at least 30% video in a feed for it
to be publishable on the Channel Guide (we're primarily a video
application, after all).""")
        paragraphs.append("""\
Once you have adequate video in your feed, please post a message 
for us on the channel page (%s), and we'll work on getting it
approved.""" % channel.get_absolute_url())
    else:
        raise ValueError("Unknown rejection reason: %s" % reason)
    body = '%s\n%s\n' % (header, 
            '\n\n'.join(p.replace('\n', ' ') for p in paragraphs))
    note = ChannelNote(user, title, body, ChannelNote.MODERATOR_TO_OWNER)
    note.channel = channel
    return note
