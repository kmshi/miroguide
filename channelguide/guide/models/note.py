import logging

from django.conf import settings

from channelguide import util
from channelguide.guide import tables, emailmessages
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
        for mod in query.execute(connection):
            message = emailmessages.ModeratorBoardEmail(self)
            message.send_email(mod.email, self.user.email)

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
        if self.channel.owner.email is not None:
            message = emailmessages.ChannelNoteEmail(self)
            message.send_email(self.channel.owner.email, self.user.email)
        else:
            logging.warn("not sending message for channel %d (%s) because "
                    "the owner email is not set", self.channel.id,
                    self.channel.name)
