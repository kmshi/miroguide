from channelguide.guide.models import User, ModeratorPost
from channelguide.testframework import TestCase

class EmailDisableTest(TestCase):
    def setUp(self):
        TestCase.setUp(self)
        self.jane = self.make_user("jane", role=User.MODERATOR)
        self.bob = self.make_user("bob", role=User.MODERATOR)
        self.stacy = self.make_user("stacy")
        self.channel = self.make_channel(self.stacy)

    def check_email_list(self, *recipients):
        correct_list = [user.email for user in recipients]
        self.assertSameSet(self.emails[0]['recipient_list'], correct_list)

    def test_disable_moderater_post_emails(self):
        self.jane.moderator_board_emails = False
        self.bob.moderator_board_emails = True
        self.jane.save(self.connection)
        self.bob.save(self.connection)
        note = ModeratorPost(self.bob, 'hi', 'body')
        note.send_email(self.connection, self.bob)
        self.check_email_list(self.bob)

    def test_webpages(self):
        self.login("bob")
        self.post_data('/accounts/moderator-board-emails/%d' % self.bob.id,
                {'set-to': 'enable'})
        self.update_bob()
        self.assertEquals(self.bob.moderator_board_emails, True)
        self.post_data('/accounts/moderator-board-emails/%d' % self.bob.id,
                {'set-to': 'disable'})
        self.update_bob()
        self.assertEquals(self.bob.moderator_board_emails, False)

        self.post_data('/accounts/status-emails/%d' % self.bob.id,
                {'set-to': 'enable'})
        self.update_bob()
        self.assertEquals(self.bob.status_emails, True)
        self.post_data('/accounts/status-emails/%d' % self.bob.id,
                {'set-to': 'disable'})
        self.update_bob()
        self.assertEquals(self.bob.status_emails, False)

    def update_bob(self):
        self.connection.commit()
        self.bob = self.refresh_record(self.bob)
