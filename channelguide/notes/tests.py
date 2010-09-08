# Copyright (c) 2008-2009 Participatory Culture Foundation
# See LICENSE for details.

from datetime import datetime, timedelta

from django.core import mail
from django.conf import settings

from django.contrib.auth.models import User
from channelguide.channels.models import Channel
from channelguide.user_profile.models import UserProfile
from channelguide.notes.models import ChannelNote, ModeratorPost
from channelguide.testframework import TestCase
from channelguide.notes.utils import get_note_info

class NotesTest(TestCase):
    def setUp(self):
        TestCase.setUp(self)
        self.channel_owner = self.make_user('foobar')
        self.channel_owner.email = 'someone@somewhere.net'
        self.channel_owner.save()
        self.channel = self.make_channel(self.channel_owner)
        self.non_owner = self.make_user('tony')
        self.moderator = self.make_user('greg', group='cg_moderator')
        self.moderator_note = self.make_note('foo')
        self.owner_note = self.make_note('bar')
        self.channel.notes.add(self.moderator_note)
        self.channel.notes.add(self.owner_note)

    def make_note(self, body):
        return ChannelNote(user=self.channel_owner, body=body)

    def assertSameNote(self, note1, note2):
        self.assertEquals(note1.title, note2.title)

    def assertSameNoteList(self, notelist1, notelist2):
        self.assertEquals(len(notelist1), len(notelist2))
        for note1, note2 in zip(notelist1, notelist2):
            self.assertSameNote(note1, note2)

    def test_add_note(self):
        notes = ChannelNote.objects.all()
        self.assertEquals(len(notes), 2)
        self.assertSameNote(notes[0], self.moderator_note)
        self.assertSameNote(notes[1], self.owner_note)

    def check_non_owner_notes(self, notes):
        self.assertEquals(notes, [])

    def check_owner_notes(self, notes):
        self.assertSameNoteList(notes, [self.owner_note, self.moderator_note])

    def test_get_note_info(self):
        self.check_non_owner_notes(
                get_note_info(self.channel, self.non_owner))
        self.check_owner_notes(
                get_note_info(self.channel, self.channel_owner))
        self.check_owner_notes(
                get_note_info(self.channel, self.moderator))

    def test_channel_page(self):
        """
        On the channel edit page, if  the user is not the owner or no user is
        logged in, no notes should be displayed.  If the user is the owner,
        display the notes for the owner.  If the user is a moderator, display
        all the notes.
        """
        channel_path = "/channels/edit/%d" % self.channel.id
        page = self.get_page(channel_path, self.channel_owner)
        self.check_owner_notes(page.context[0]['notes'])
        page = self.get_page(channel_path, self.moderator)
        self.check_owner_notes(page.context[0]['notes'])

class NotesPageTestBase(TestCase):
    def setUp(self):
        TestCase.setUp(self)
        self.user = self.make_user('fred')
        self.moderator = self.make_user('greg', group='cg_moderator')
        self.supermod = self.make_user('henrietta', group=['cg_supermoderator',
                                                           'cg_moderator'])
        self.random_user = self.make_user("jane")
        self.user.email = 'someone@somewhere.net'
        self.user.save()
        self.channel = self.make_channel(self.user)

    def make_note_post_data(self):
        post_data = {
                'channel-id': self.channel.id,
                'body': 'test body',
            }
        return post_data


class NotesPageTest(NotesPageTestBase):
    def test_add_note(self):
        self.login(self.user)
        post_data = self.make_note_post_data()
        self.post_data("/notes/new", post_data)
        self.check_note_count(1)
        self.assertEquals(self.channel.notes.all()[0].body, post_data['body'])
        self.assertEquals(len(mail.outbox), 0)
        self.login(self.moderator)
        self.post_data("/notes/new", post_data)
        self.check_note_count(2)
        self.assertEquals(len(mail.outbox), 1)

    def add_note_to_channel(self):
        start_count = self.get_note_count()
        note = ChannelNote(self.user, 'test')
        self.channel.notes.add(note)
        self.check_note_count(start_count + 1)
        return note

    def get_note_count(self):
        return self.channel.notes.count()

    def check_note_count(self, correct_count):
        self.assertEquals(self.get_note_count(), correct_count)

    def check_can_add(self, user, can_add):
        if user is not None:
            self.login(user)
        start_count = self.get_note_count()
        page = self.post_data("/notes/new", self.make_note_post_data())
        if can_add:
            self.check_note_count(start_count + 1)
        else:
            self.assertLoginRedirect(page)

    def test_add_auth(self):
        self.check_can_add(None, False)
        self.check_can_add(self.random_user, False)
        self.check_can_add(self.user, True)
        self.check_can_add(self.moderator, True)
        self.check_can_add(self.supermod, True)

    def check_can_email(self, user, can_email):
        start_count = len(mail.outbox)
        if user is not None:
            self.login(user)
        self.post_data("/notes/new", self.make_note_post_data())
        if can_email:
            self.assertEquals(len(mail.outbox), start_count + 1)
        else:
            self.assertEquals(len(mail.outbox), start_count)

    def test_email_from(self):
        self.login(self.moderator)
        self.post_data("/notes/new", self.make_note_post_data())
        self.assertEquals(mail.outbox[0].from_email, settings.EMAIL_FROM)

    def test_channel_link(self):
        self.login(self.moderator)
        self.post_data("/notes/new", self.make_note_post_data())
        self.assert_(self.channel.get_absolute_url() in
                     mail.outbox[0].body)

    def test_email_auth(self):
        self.check_can_email(None, False)
        self.check_can_email(self.random_user, False)
        self.check_can_email(self.user, False)
        self.check_can_email(self.moderator, True)
        self.check_can_email(self.supermod, True)

class ModeratorPostTest(TestCase):
    def setUp(self):
        TestCase.setUp(self)
        self.user = self.make_user('user')
        self.mod = self.make_user('mod', group='cg_moderator')
        self.supermod = self.make_user('supermod', group=['cg_moderator',
                                                          'cg_supermoderator'])
        self.new_post_data = {
            'title': 'test title',
            'body': 'test body',
        }
        self.new_post_data_email = self.new_post_data.copy()
        self.new_post_data_email['send-email'] = 1

    def add_post(self):
        ModeratorPost(user=self.mod, title='test', body='test').save()

    def get_post_count(self):
        return ModeratorPost.objects.count()

    def test_board(self):
        self.post_data('/notes/new-moderator-post', self.new_post_data,
                       login_as=self.supermod)
        response = self.get_page('/notes/moderator-board', login_as=self.mod)
        self.assertEquals(response.status_code, 200)
        page = response.context['page']
        self.assertEquals(page.object_list.count(), 1)
        self.assertEquals(page.object_list[0].title,
                          self.new_post_data['title'])
        self.assertEquals(page.object_list[0].body,
                          self.new_post_data['body'])

    def test_view_auth(self):
        self.assertLoginRedirect("/notes/moderator-board")
        self.assertLoginRedirect("/notes/moderator-board", self.user)
        self.assertCanAccess("/notes/moderator-board", self.mod)
        self.assertCanAccess("/notes/moderator-board", self.supermod)

    def check_add_auth(self, user, can_add):
        start_count = self.get_post_count()
        page = self.post_data('/notes/new-moderator-post', self.new_post_data,
                login_as=user)
        if can_add:
            self.assertEqual(self.get_post_count(), start_count + 1)
        else:
            self.assertLoginRedirect(page)
            self.assertEqual(self.get_post_count(), start_count)

    def test_add(self):
        self.check_add_auth(None, False)
        self.check_add_auth(self.user, False)
        self.check_add_auth(self.mod, True)
        self.check_add_auth(self.supermod, True)

    def check_delete_auth(self, user, can_delete):
        start_count = self.get_post_count()
        post = ModeratorPost.objects.all()[0]
        page = self.post_data('/notes/post-%d' % post.id,
                {'action' : 'delete'}, login_as=user)
        if can_delete:
            self.assertEqual(self.get_post_count(), start_count - 1)
        else:
            self.assertLoginRedirect(page)
            self.assertEqual(self.get_post_count(), start_count)

    def test_delete(self):
        for i in range(5):
            self.add_post()
        self.check_delete_auth(None, False)
        self.check_delete_auth(self.user, False)
        self.check_delete_auth(self.mod, False)
        self.check_delete_auth(self.supermod, True)

    def moderators(self):
        return [user for user in User.objects.exclude(
                userprofile__moderator_board_email=UserProfile.NO_EMAIL)
                if user.has_perm('notes.add_moderatorpost')]

    def check_email_auth(self, user, can_email):
        start_count = len(mail.outbox)
        self.post_data('/notes/new-moderator-post',
                       self.new_post_data_email, login_as=user)
        if can_email:
            self.assertEqual(len(mail.outbox), start_count +
                    len(self.moderators()))
            self.assertEquals(mail.outbox[-1].from_email, user.email)
        else:
            self.assertEqual(len(mail.outbox), start_count)

    def test_email(self):
        self.check_email_auth(None, False)
        self.check_email_auth(self.user, False)
        self.check_email_auth(self.mod, True)
        self.check_email_auth(self.supermod, True)

    def test_email_without_email(self):
        self.supermod.email = ''
        self.supermod.save()
        self.post_data('/notes/new-moderator-post',
                       self.new_post_data_email, login_as=self.supermod)
        self.assertEquals(mail.outbox[-1].from_email, settings.EMAIL_FROM)

    def test_to_lines(self):
        self.post_data('/notes/new-moderator-post',
                self.new_post_data_email, login_as=self.supermod)

        sent_emails = set()
        for e in mail.outbox:
            for recipient in e.recipients():
                if recipient in sent_emails:
                    raise AssertionError("Duplicate to")
                sent_emails.add(recipient)
        mod_emails = [mod.email for mod in self.moderators()]
        self.assertSameSet(sent_emails, mod_emails)

class WaitingForReplyTest(NotesPageTestBase):
    def make_user_post(self):
        self.login(self.user)
        self.post_data("/notes/new", self.make_note_post_data())

    def test_waiting_for_reply(self):
        self.assertEquals(self.channel.waiting_for_reply_date, None)
        self.make_user_post()
        updated = Channel.objects.get(pk=self.channel.pk)
        self.assertNotEqual(updated.waiting_for_reply_date, None)
        timediff = datetime.now() - updated.waiting_for_reply_date
        self.assert_(timediff < timedelta(seconds=1))

    def test_waiting_for_reply_moderator_post(self):
        self.make_user_post()
        self.login(self.moderator)
        self.post_data("/notes/new", self.make_note_post_data())
        updated = Channel.objects.get(pk=self.channel.pk)
        self.assertEquals(updated.waiting_for_reply_date, None)

    def test_waiting_for_reply_moderator_unflag(self):
        self.make_user_post()
        data = {'action': 'mark-replied'}
        response = self.post_data('/channels/%d' % self.channel.id, data)
        self.assertLoginRedirect(response)
        updated = Channel.objects.get(pk=self.channel.pk)
        self.assertNotEqual(updated.waiting_for_reply_date, None)
        self.login(self.moderator)
        response = self.post_data('/channels/%d' % self.channel.id, data)
        updated = Channel.objects.get(pk=self.channel.pk)
        self.assertEqual(updated.waiting_for_reply_date, None)

    def test_waiting_for_reply_order(self):
        channel1 = self.make_channel(self.user)
        channel2 = self.make_channel(self.user)
        channel3 = self.make_channel(self.user)
        channel1.waiting_for_reply_date = datetime.now()
        channel2.waiting_for_reply_date = datetime.now() - timedelta(days=1)
        channel3.waiting_for_reply_date = datetime.now() - timedelta(days=2)
        channel1.save()
        channel2.save()
        channel3.save()

        self.login(self.moderator)
        page = self.get_page('/moderate/waiting')
        page_channel_ids = [c.id for c in page.context[0]['page'].object_list]
        self.assertEquals(page_channel_ids,
                [channel3.id, channel2.id, channel1.id])


class EmailDisableTest(TestCase):
    def setUp(self):
        TestCase.setUp(self)
        self.jane = self.make_user("jane", group='cg_moderator')
        self.bob = self.make_user("bob", group='cg_moderator')
        self.brian = self.make_user("brian", group='cg_moderator')
        self.stacy = self.make_user("stacy")
        self.channel = self.make_channel(self.stacy)

    def check_email_list(self, *recipients):
        correct_list = [user.email for user in recipients]
        self.assertSameSet(self.email_recipients(), correct_list)

    def test_disable_moderater_post_emails(self):
        self.jane.get_profile().moderator_board_email = UserProfile.NO_EMAIL
        self.bob.get_profile().moderator_board_email = UserProfile.SOME_EMAIL
        self.brian.get_profile().moderator_board_email = UserProfile.ALL_EMAIL
        self.jane.get_profile().save()
        self.bob.get_profile().save()
        self.brian.get_profile().save()
        note = ModeratorPost(user=self.bob,
                             title='hi',
                             body='body')
        note.send_email(True)
        self.check_email_list(self.bob, self.brian)
        mail.outbox = []
        note.send_email(False)
        self.check_email_list(self.brian)
