from datetime import datetime, timedelta

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
        self.moderator_note = self.make_note('foo', ChannelNote.MODERATOR_ONLY)
        self.owner_note = self.make_note('bar', ChannelNote.MODERATOR_TO_OWNER)
        self.channel.notes.add_record(self.connection, self.moderator_note)
        self.channel.notes.add_record(self.connection, self.owner_note)
        self.connection.commit()

    def make_note(self, title, type):
        return ChannelNote(self.channel_owner, title, 'Booya', type)

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
        self.assertEquals(notes['show_owner_notes'], False)
        self.assertSameNoteList(notes['owner_notes'], [])
        self.assertEquals(notes['show_moderator_notes'], False)
        self.assertSameNoteList(notes['moderator_notes'], [])

    def check_owner_notes(self, notes):
        self.assertEquals(notes['show_owner_notes'], True)
        self.assertSameNoteList(notes['owner_notes'], [self.owner_note])
        self.assertEquals(notes['show_moderator_notes'], False)
        self.assertSameNoteList(notes['moderator_notes'], [])

    def check_moderator_notes(self, notes):
        self.assertEquals(notes['show_owner_notes'], True)
        self.assertSameNoteList(notes['owner_notes'], [self.owner_note])
        self.assertEquals(notes['show_moderator_notes'], True)
        self.assertSameNoteList(notes['moderator_notes'], [self.moderator_note])

    def test_get_note_info(self):
        self.check_non_owner_notes(
                get_note_info(self.channel, self.non_owner))
        self.check_owner_notes(
                get_note_info(self.channel, self.channel_owner))
        self.check_moderator_notes(
                get_note_info(self.channel, self.moderator))

    def test_channel_page(self):
        channel_path = "/channels/%d" % self.channel.id
        page = self.get_page(channel_path)
        self.check_non_owner_notes(page.context[0]['notes'])
        page = self.get_page(channel_path, self.non_owner)
        self.check_non_owner_notes(page.context[0]['notes'])
        page = self.get_page(channel_path, self.channel_owner)
        self.check_owner_notes(page.context[0]['notes'])
        page = self.get_page(channel_path, self.moderator)
        self.check_moderator_notes(page.context[0]['notes'])

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

    def make_note_post_data(self, send_email=False, 
            type=ChannelNote.MODERATOR_ONLY):
        post_data = {
                'channel-id': self.channel.id,
                'title': 'test title',
                'body': 'test body',
            }
        if type == ChannelNote.MODERATOR_ONLY:
            post_data['type'] = 'moderator-only'
        else:
            post_data['type'] = 'moderator-to-owner'
        if send_email:
            post_data['send-email'] = 1
        return post_data


class NotesPageTest(NotesPageTestBase):
    def test_add_note(self):
        self.login(self.moderator)
        post_data = self.make_note_post_data()
        page = self.post_data("/notes/new", post_data)
        self.channel = self.refresh_record(self.channel, 'notes')
        self.assertEquals(len(self.channel.notes), 1)
        self.assertEquals(self.channel.notes[-1].title, post_data['title'])
        self.assertEquals(self.channel.notes[-1].body, post_data['body'])
        self.assertEquals(self.channel.notes[-1].type,
                ChannelNote.MODERATOR_ONLY)
        self.assertEquals(len(self.emails), 0)
        page = self.post_data("/notes/new", self.make_note_post_data(True))
        self.channel = self.refresh_record(self.channel, 'notes')
        self.assertEquals(len(self.channel.notes), 2)
        self.assertEquals(len(self.emails), 1)

    def test_email_checkbox(self):
        channel_path = "/channels/%d" % self.channel.id
        page = self.get_page(channel_path, self.user)
        self.assert_('send-email' not in str(page))
        page = self.get_page(channel_path, self.moderator)
        self.assert_('send-email' in str(page))

    def add_note_to_channel(self):
        start_count = self.get_note_count()
        note = ChannelNote(self.user, 'test', 'test',
                ChannelNote.MODERATOR_TO_OWNER)
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

    def test_delete_note(self):
        note = self.add_note_to_channel()
        self.login(self.moderator)
        page = self.post_data("/notes/%d" % note.id, {'action' : 'delete'})
        self.check_note_count(0)

    def check_can_delete(self, user, can_delete):
        start_note_count = self.get_note_count()
        self.channel = self.refresh_record(self.channel, 'notes')
        if user is not None:
            self.login(user)
        page = self.post_data("/notes/%d" % self.channel.notes[0].id, 
                {'action' : 'delete'})
        if can_delete:
            self.check_note_count(start_note_count - 1)
        else:
            self.assertLoginRedirect(page)
            self.check_note_count(start_note_count)

    def test_delete_auth(self):
        for x in range(5):
            self.add_note_to_channel()
        self.check_note_count(5)
        self.check_can_delete(None, False)
        self.check_can_delete(self.random_user, False)
        self.check_can_delete(self.user, False)
        self.check_can_delete(self.moderator, True)
        self.check_can_delete(self.supermod, True)

    def check_can_add(self, user, can_add_normal, can_add_moderator_only):
        if user is not None:
            self.login(user)
        def do_check(post_data, can_add):
            start_count = self.get_note_count()
            page = self.post_data("/notes/new", post_data)
            if can_add:
                self.check_note_count(start_count + 1)
            else:
                self.assertLoginRedirect(page)
                self.check_note_count(start_count)
        do_check(self.make_note_post_data(), can_add_moderator_only)
        do_check(self.make_note_post_data(type=ChannelNote.MODERATOR_TO_OWNER), 
                can_add_normal)

    def test_add_auth(self):
        self.check_can_add(None, False, False)
        self.check_can_add(self.random_user, False, False)
        self.check_can_add(self.user, True, False)
        self.check_can_add(self.moderator, True, True)
        self.check_can_add(self.supermod, True, True)

    def check_can_email(self, user, can_email):
        start_count = len(self.emails)
        if user is not None:
            self.login(user)
        page = self.post_data("/notes/new", self.make_note_post_data(True))
        if can_email:
            self.assertEquals(len(self.emails), start_count + 1)
        else:
            self.assertEquals(len(self.emails), start_count)

    def test_email_from(self):
        self.login(self.moderator)
        page = self.post_data("/notes/new", self.make_note_post_data(True))
        self.assertEquals(self.emails[0]['email_from'], self.moderator.email)

    def test_channel_link(self):
        self.login(self.moderator)
        page = self.post_data("/notes/new", self.make_note_post_data(True))
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
        query = User.query(User.c.role.in_(User.ALL_MODERATOR_ROLES))
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

    def test_email_from(self):
        self.post_data('/notes/new-moderator-post',
                self.new_post_data_email, login_as=self.supermod)
        self.assertEquals(self.emails[0]['email_from'], self.supermod.email)

    def test_to_lines(self):
        self.post_data('/notes/new-moderator-post',
                self.new_post_data_email, login_as=self.supermod)

        sent_emails = set()
        for e in self.emails:
            for recipient in e['recipient_list']:
                if recipient in sent_emails:
                    raise AssertionError("Duplicate to")
                sent_emails.add(recipient)
        query = User.query(User.c.role.in_(User.ALL_MODERATOR_ROLES))
        mod_emails = [mod.email for mod in query.execute(self.connection)]
        self.assertSameSet(sent_emails, mod_emails)

class WaitingForReplyTest(NotesPageTestBase):
    def make_user_post(self):
        self.login(self.user)
        self.post_data("/notes/new", self.make_note_post_data(
                type=ChannelNote.MODERATOR_TO_OWNER))

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
        self.post_data("/notes/new", self.make_note_post_data(
                type=ChannelNote.MODERATOR_TO_OWNER))
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
