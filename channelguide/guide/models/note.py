from django.utils.translation import gettext as _

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

    def send_email(self, connection, sender):
        query = User.query()
        query.where(User.c.role.in_(User.ALL_MODERATOR_ROLES))
        query.where(moderator_board_emails=True)
        query.where(User.c.email.is_not(None))
        emails = [mod.email for mod in query.execute(connection)]
        util.send_mail(self.title, self.body, emails, email_from=sender.email)

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

    def send_email(self, sender):
        header = _("""\
A note was added to your channel at channelguide.participatoryculture.org.
You can view your channel here: %s.
The contents of the note are below...""") % self.channel.get_absolute_url()
        separator = '-' * 70
        full_body = '%s\n%s\n\n%s' % (header, separator, self.body)

        util.send_mail(self.title, full_body, self.channel.owner.email,
                email_from=sender.email)
