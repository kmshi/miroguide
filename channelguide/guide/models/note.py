from channelguide import util
from channelguide.db import DBObject
from user import User

class NoteBase(DBObject):
    def __init__(self, user, title, body):
        self.user = user
        self.title = title
        self.body = body

class ModeratorPost(NoteBase):
    @staticmethod
    def create_note_from_request(request):
        """Create a moderator post using a request from a create post form. """

        if not request.user.is_moderator():
            raise ValueError("User is not a moderator")
        return ModeratorPost(request.user, request.POST['title'],
                request.POST['body'])

    def get_absolute_url(self):
        return util.make_url("notes/post-%d" % self.id)

    def send_email(self, sender):
        query = self.session().query(User)
        moderators = query.select(User.c.role.in_(*User.ALL_MODERATOR_ROLES))
        emails = [mod.email for mod in moderators 
                if mod.moderator_board_emails and mod.email is not None]
        util.send_mail(self.title, self.body, emails, email_from=sender.email)

class ChannelNote(NoteBase):
    # codes for the type column
    MODERATOR_ONLY = 'M'
    MODERATOR_TO_OWNER = 'O'

    def __init__(self, user, title, body, type):
        super(ChannelNote, self).__init__(user, title, body)
        self.type = type

    def get_absolute_url(self):
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
        util.send_mail(self.title, self.body, self.channel.owner.email,
                email_from=sender.email)
