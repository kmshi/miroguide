import textwrap

from django.conf import settings

from channelguide import util
from channelguide.guide import tables
from sqlhelper.orm import Record
from user import User

class NoteBase(Record):
    def __init__(self, user, title, body):
        self.user = user
        self.title = title
        self.body = body

class ModeratorPost(NoteBase):
    table = tables.moderator_post

    @staticmethod
    def create_note_from_request(request):
        """Create a moderator post using a request from a create post form. """

        if not request.user.is_moderator():
            raise ValueError("User is not a moderator")
        return ModeratorPost(request.user, request.POST['title'],
                request.POST['body'])

    def get_url(self):
        return util.make_url("notes/post-%d" % self.id)

    def send_email(self, connection, send_checked):
        query = User.query()
        query.where(User.c.role.in_(User.ALL_MODERATOR_ROLES))
        if send_checked:
            values = [User.ALL_EMAIL, User.SOME_EMAIL]
            query.where(User.c.moderator_board_email.in_(values))
        else:
            query.where(moderator_board_email=User.ALL_EMAIL)
        query.where(User.c.email.is_not(None))
        emails = [mod.email for mod in query.execute(connection)]
        util.send_mail(self.title, self.body, emails, email_from=self.user.email)

class ChannelNote(NoteBase):
    table = tables.channel_note

    # codes for the type column
    MODERATOR_ONLY = 'M'
    MODERATOR_TO_OWNER = 'O'

    def __init__(self, user, title, body, type):
        super(ChannelNote, self).__init__(user, title, body)
        self.type = type

    def get_url(self):
        return util.make_url("notes/%d" % self.id)

    @staticmethod
    def create_note_from_request(request):
        """Create a channel note using a request from an add note form. """

        if request.POST['type'] == 'moderator-only':
            note_type = ChannelNote.MODERATOR_ONLY
        elif request.POST['type'] == 'moderator-to-owner':
            note_type = ChannelNote.MODERATOR_TO_OWNER
        else:
            raise ValueError("Invalid not type")
        return ChannelNote(request.user, request.POST['title'],
                request.POST['body'], note_type)

    def send_email(self, connection):
        self.join('channel').execute(connection)
        self.channel.join('owner').execute(connection)
        wrapped_body = '\n'.join(textwrap.fill(p) for p in
                self.body.split('\n'))

        email_body = """\
A moderator of the Channel Guide added the following note to your channel:

%s

%s

You may review and respond to the note here: %s""" % \
            (self.title, wrapped_body, self.channel.get_absolute_url())
        email_title = '[Channel Guide] Note for %s' % self.channel.name
        util.send_mail(email_title, email_body, self.channel.owner.email,
                self.user.email)
