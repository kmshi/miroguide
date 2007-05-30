from channelguide.guide.models import User, ModeratorPost
from channelguide.testframework import TestCase

class EmailDisableTest(TestCase):
    def setUp(self):
        TestCase.setUp(self)
        self.jane = self.make_user("jane", role=User.MODERATOR)
        self.bob = self.make_user("bob", role=User.MODERATOR)
        self.brian = self.make_user("brian", role=User.MODERATOR)
        self.stacy = self.make_user("stacy")
        self.channel = self.make_channel(self.stacy)

    def check_email_list(self, *recipients):
        correct_list = [user.email for user in recipients]
        sent_to = []
        for email in self.emails:
            sent_to.extend(email['recipient_list'])
        self.assertSameSet(sent_to, correct_list)

    def test_disable_moderater_post_emails(self):
        self.jane.moderator_board_email = User.NO_EMAIL
        self.bob.moderator_board_email = User.SOME_EMAIL
        self.brian.moderator_board_email = User.ALL_EMAIL
        self.jane.save(self.connection)
        self.bob.save(self.connection)
        self.brian.save(self.connection)
        note = ModeratorPost(self.bob, 'hi', 'body')
        note.send_email(self.connection, self.bob, True)
        self.check_email_list(self.bob, self.brian)
        self.emails = []
        note.send_email(self.connection, self.bob, False)
        self.check_email_list(self.brian)
