# Copyright (c) 2008-2009 Participatory Culture Foundation
# See LICENSE for details.

from datetime import datetime
import logging

from django.db import models

from django.contrib.auth.models import User
from channelguide.user_profile.models import UserProfile
from channelguide import util
from channelguide.guide import emailmessages

class NoteBase(models.Model):
    user = models.ForeignKey('auth.User', related_name='%(class)s_notes')
    title = models.CharField(max_length=255)
    body = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        abstract = True

class ModeratorPost(NoteBase):

    class Meta(NoteBase.Meta):
        db_table = 'cg_moderator_post'

    @staticmethod
    def create_note_from_request(request):
        """Create a moderator post using a request from a create post form. """

        if not request.user.has_perm('notes.add_moderatorpost'):
            raise ValueError("User is not a moderator")
        return ModeratorPost(user=request.user, title=request.POST['title'],
                             body=request.POST['body'])

    def get_url(self):
        return util.make_url("notes/post-%d" % self.id)

    def send_email(self, send_checked):
        if send_checked:
            values = [UserProfile.ALL_EMAIL, UserProfile.SOME_EMAIL]
            query = User.objects.filter(
                userprofile__moderator_board_email__in=values)
        else:
            query = User.objects.filter(
                userprofile__moderator_board_email=UserProfile.ALL_EMAIL)
        query = query.exclude(email='')
        for user in query:
            if user.has_perm('notes.add_moderatorpost'):
                message = emailmessages.ModeratorBoardEmail(self)
                message.send_email(user.email, self.user.email or None)

class ChannelNote(NoteBase):
    channel = models.ForeignKey('channels.Channel', related_name='notes')

    class Meta(NoteBase.Meta):
        db_table = 'cg_channel_note'

    def get_url(self):
        return util.make_url("notes/%d" % self.id)

    @staticmethod
    def create_note_from_request(request):
        """Create a channel note using a request from an add note form. """

        return ChannelNote(user=request.user,
                           title='',
                           body=request.POST['body'])

    def send_email(self, email=None):
        if email is None:
            email = self.channel.owner.email
        if email is not None:
            message = emailmessages.ChannelNoteEmail(self)
            message.send_email(email)
        else:
            logging.warn("not sending message for channel %d (%s) because "
                    "the owner email is not set", self.channel.id,
                    self.channel.name)

from django.db.models import signals

def channel_note_added(instance=None, **kwargs):
    if instance.user == instance.channel.owner or \
            not instance.user.has_perm('channels.change_channel'):
        instance.channel.waiting_for_reply_date = datetime.now()
        instance.channel.save()
    elif instance.channel.waiting_for_reply_date is not None:
        instance.channel.waiting_for_reply_date = None
        instance.channel.save()


signals.post_save.connect(channel_note_added, sender=ChannelNote)
