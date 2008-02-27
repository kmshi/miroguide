# Copyright (c) 2008 Participatory Culture Foundation
# See LICENSE for details.

from datetime import datetime, timedelta

from django.conf import settings
from django.test.client import Client

from channelguide.guide.models import User, Channel, ChannelNote, ModeratorPost
from channelguide.testframework import TestCase
from channelguide.guide.notes import get_note_info

class NotesTest(TestCase):
    def setUp(self):
        TestCase.setUp(self)
        self.channel_owner = self.make_user('foobar')
        self.channel_owner.email = 'someone@somewhere.net'
        self.channel_owner.save(self.connection)
        self.channel = self.make_channel(self.channel_owner)
        self.channel.join("notes").execute(self.connection)
        self.non_owner = self.make_user('tony')
        self.moderator = self.make_user('greg', role=User.MODERATOR)
        self.moderator_note = self.make_note('foo')
        self.owner_note = self.make_note('bar')
        self.channel.notes.add_record(self.connection, self.moderator_note)
        self.channel.notes.add_record(self.connection, self.owner_note)
        self.connection.commit()

    def make_note(self, body):
        return ChannelNote(self.channel_owner, body)

    def assertSameNote(self, note1, note2):
        self.assertEquals(note1.title, note2.title)

    def assertSameNoteList(self, notelist1, notelist2):
        self.assertEquals(len(notelist1), len(notelist2))
        for note1, note2 in zip(notelist1, notelist2):
            self.assertSameNote(note1, note2)

    def test_add_note(self):
        notes = ChannelNote.query().execute(self.connection)
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
        self.moderator = self.make_user('greg', role=User.MODERATOR)
        self.supermod = self.make_user('henrietta', role=User.SUPERMODERATOR)
        self.random_user = self.make_user("jane")
        self.user.email = 'someone@somewhere.net'
        self.user.save(self.connection)
        self.channel = self.make_channel(self.user)
        self.channel.join('notes').execute(self.connection)

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
        page = self.post_data("/notes/new", post_data)
        self.channel = self.refresh_record(self.channel, 'notes')
        self.assertEquals(len(self.channel.notes), 1)
        self.assertEquals(self.channel.notes[-1].body, post_data['body'])
        self.assertEquals(len(self.emails), 0)
        self.login(self.moderator)
        page = self.post_data("/notes/new", post_data)
        self.channel = self.refresh_record(self.channel, 'notes')
        self.assertEquals(len(self.channel.notes), 2)
        self.assertEquals(len(self.emails), 1)

    def add_note_to_channel(self):
        start_count = self.get_note_count()
        note = ChannelNote(self.user, 'test')
        self.channel.notes.add_record(self.connection, note)
        self.check_note_count(start_count + 1)
        return note

    def get_note_count(self):
        self.connection.commit()
        updated_channel = self.refresh_record(self.channel)
        updated_channel.join("notes").execute(self.connection)
        return len(updated_channel.notes)

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
        start_count = len(self.emails)
        if user is not None:
            self.login(user)
        page = self.post_data("/notes/new", self.make_note_post_data())
        if can_email:
            self.assertEquals(len(self.emails), start_count + 1)
        else:
            self.assertEquals(len(self.emails), start_count)

    def test_email_from(self):
        self.login(self.moderator)
        page = self.post_data("/notes/new", self.make_note_post_data())
        self.assertEquals(self.emails[0]['email_from'], settings.EMAIL_FROM)

    def test_channel_link(self):
        self.login(self.moderator)
        page = self.post_data("/notes/new", self.make_note_post_data())
        self.assert_(self.channel.get_absolute_url() in self.emails[0]['body'])

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
        self.mod = self.make_user('mod', role=User.MODERATOR)
        self.supermod = self.make_user('supermod', role=User.SUPERMODERATOR)
        self.new_post_data = {
            'title': 'test title',
            'body': 'test body',
        }
        self.new_post_data_email = self.new_post_data.copy()
        self.new_post_data_email['send-email'] = 1

    def add_post(self):
        ModeratorPost(self.mod, 'test', 'test').save(self.connection)
        
    def get_post_count(self):
        self.refresh_connection()
        return ModeratorPost.query().count(self.connection)

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
        post = ModeratorPost.query().limit(1).get(self.connection)
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

    def moderater_count(self):
        query = User.query(User.c.role.in_(User.ALL_MODERATOR_ROLES),
                User.c.moderator_board_email!=User.NO_EMAIL)
        return query.count(self.connection)

    def check_email_auth(self, user, can_email):
        start_count = len(self.emails)
        page = self.post_data('/notes/new-moderator-post',
                self.new_post_data_email, login_as=user)
        if can_email:
            self.assertEqual(len(self.emails), start_count +
                    self.moderater_count())
        else:
            self.assertEqual(len(self.emails), start_count)

    def test_email(self):
        self.check_email_auth(None, False)
        self.check_email_auth(self.user, False)
        self.check_email_auth(self.mod, False)
        self.check_email_auth(self.supermod, True)

    def test_to_lines(self):
        self.post_data('/notes/new-moderator-post',
                self.new_post_data_email, login_as=self.supermod)

        sent_emails = set()
        for e in self.emails:
            for recipient in e['recipient_list']:
                if recipient in sent_emails:
                    raise AssertionError("Duplicate to")
                sent_emails.add(recipient)
        query = User.query(User.c.role.in_(User.ALL_MODERATOR_ROLES),
                User.c.moderator_board_email!=User.NO_EMAIL)
        mod_emails = [mod.email for mod in query.execute(self.connection)]
        self.assertSameSet(sent_emails, mod_emails)

class WaitingForReplyTest(NotesPageTestBase):
    def make_user_post(self):
        self.login(self.user)
        self.post_data("/notes/new", self.make_note_post_data())

    def test_waiting_for_reply(self):
        self.assertEquals(self.channel.waiting_for_reply_date, None)
        self.make_user_post()
        updated = self.refresh_record(self.channel)
        self.assertNotEqual(updated.waiting_for_reply_date, None)
        timediff = datetime.now() - updated.waiting_for_reply_date
        self.assert_(timediff < timedelta(seconds=1))

    def test_waiting_for_reply_moderator_post(self):
        self.make_user_post()
        self.login(self.moderator)
        self.post_data("/notes/new", self.make_note_post_data())
        updated = self.refresh_record(self.channel)
        self.assertEquals(updated.waiting_for_reply_date, None)

    def test_waiting_for_reply_moderator_unflag(self):
        self.make_user_post()
        data = {'action': 'mark-replied'}
        response = self.post_data('/channels/%d' % self.channel.id, data)
        self.assertLoginRedirect(response)
        updated = self.refresh_record(self.channel)
        self.assertNotEqual(updated.waiting_for_reply_date, None)
        self.login(self.moderator)
        response = self.post_data('/channels/%d' % self.channel.id, data)
        updated = self.refresh_record(self.channel)
        self.assertEqual(updated.waiting_for_reply_date, None)

    def test_waiting_for_reply_order(self):
        channel1 = self.make_channel(self.user)
        channel2 = self.make_channel(self.user)
        channel3 = self.make_channel(self.user)
        channel1.waiting_for_reply_date = datetime.now()
        channel2.waiting_for_reply_date = datetime.now() - timedelta(days=1)
        channel3.waiting_for_reply_date = datetime.now() - timedelta(days=2)
        self.save_to_db(channel1)
        self.save_to_db(channel2)
        self.save_to_db(channel3)

        self.login(self.moderator)
        page = self.get_page('/channels/moderator-list/waiting')
        page_channel_ids = [c.id for c in page.context[0]['channels']]
        self.assertEquals(page_channel_ids, 
                [channel3.id, channel2.id, channel1.id])
