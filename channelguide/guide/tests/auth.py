import os

from channelguide import db
from channelguide.guide.auth import login, logout, SESSION_KEY
from channelguide.guide.models import Channel
from channelguide.testframework import TestCase
from channelguide.util import read_file, hash_string

class AuthTest(TestCase):
    def setUp(self):
        TestCase.setUp(self)
        self.user = self.make_user('joe', 'password')

    def check_password(self):
        self.assert_(self.user.check_password('password'))
        self.assert_(not self.user.check_password('badpassword'))

    def test_middleware(self):
        request = self.process_request()
        login(request, self.user)
        response = self.process_response(request)
        request = self.process_request(cookies_from=response.cookies)
        self.assert_(request.user.is_authenticated())
        self.assertEquals(request.user.username, 'joe')
        logout(request)
        response = self.process_response(request)
        request = self.process_request(cookies_from=response.cookies)
        self.assert_(not request.user.is_authenticated())

    def test_corrupt_cookie(self):
        request = self.process_request(cookies_from={SESSION_KEY:'corrupt'})
        self.assert_(not request.user.is_authenticated())

    def test_bad_password_cookie(self):
        cookies = { SESSION_KEY: ('joe', 'badpass')}
        request = self.process_request(cookies_from=cookies)
        self.assert_(not request.user.is_authenticated())

    def test_moderator_action_count(self):
        channel = self.make_channel(self.user)
        channel2 = self.make_channel(self.user)
        def check_count(correct_count):
            self.refresh_connection()
            self.db_session.refresh(self.user)
            current_count = self.user.moderator_action_count
            self.assertEquals(current_count, correct_count)
        self.user.add_moderator_action(channel, Channel.APPROVED)
        check_count(1)
        self.user.add_moderator_action(channel, Channel.APPROVED)
        check_count(1)
        self.user.add_moderator_action(channel2, Channel.APPROVED)
        check_count(2)

