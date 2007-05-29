import os

from django.conf import settings

from channelguide import db, util
from channelguide.guide import tables
from channelguide.guide.auth import login, logout, SESSION_KEY
from channelguide.guide.models import (Channel, UserAuthToken, User,
        ModeratorAction)
from channelguide.testframework import TestCase

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
        self.process_response(request)

    def test_corrupt_cookie(self):
        request = self.process_request(cookies_from={SESSION_KEY:'corrupt'})
        self.assert_(not request.user.is_authenticated())
        self.process_response(request)

    def test_bad_password_cookie(self):
        cookies = { SESSION_KEY: ('joe', 'badpass')}
        request = self.process_request(cookies_from=cookies)
        self.assert_(not request.user.is_authenticated())
        self.process_response(request)

    def test_moderator_action_count(self):
        channel = self.make_channel(self.user)
        channel2 = self.make_channel(self.user)
        def check_count(correct_count):
            user = User.get(self.connection, self.user.id,
                    load='moderator_action_count')
            current_count = user.moderator_action_count
            self.assertEquals(current_count, correct_count)
        ModeratorAction(self.user, channel, 
                Channel.APPROVED).save(self.connection)
        check_count(1)
        ModeratorAction(self.user, channel, Channel.NEW).save(self.connection)
        check_count(1)
        ModeratorAction(self.user, channel2, 
                Channel.APPROVED).save(self.connection)
        check_count(2)

class AuthTokenTest(TestCase):
    def setUp(self):
        TestCase.setUp(self)
        self.user = self.make_user("janet")
        self.user.join("auth_token").execute(self.connection)

    def find_auth_token(self):
        token = self.user.auth_token.token
        return UserAuthToken.find_token(self.connection, token)

    def test_check(self):
        self.user.make_new_auth_token(self.connection)
        self.assert_(self.find_auth_token())

    def test_expires(self):
        self.user.make_new_auth_token(self.connection)
        self.user.auth_token.expires -= settings.AUTH_TOKEN_EXPIRATION_TIME
        self.user.auth_token.save(self.connection)
        self.assert_(not self.find_auth_token())

    def check_auth_token_count(self, count_check):
        select = tables.user_auth_token.select_count()
        count = select.execute_scalar(self.connection)
        self.assertEquals(count, count_check)

    def test_delete(self):
        self.user.make_new_auth_token(self.connection)
        self.check_auth_token_count(1)
        self.user.auth_token.delete(self.connection)
        self.check_auth_token_count(0)

    def test_update(self):
        self.user.make_new_auth_token(self.connection)
        first_token = self.user.auth_token.token
        self.user.make_new_auth_token(self.connection)
        self.check_auth_token_count(1)
        self.assertNotEqual(first_token, self.user.auth_token.token)

class AuthTokenWebTest(TestCase):
    def setUp(self):
        TestCase.setUp(self)
        self.user = self.make_user('chris')
        self.user.email = 'chris@pculture.org'

    def request_auth_token(self):
        self.post_data('/accounts/forgot-password', {'email': self.user.email})
        self.user = self.refresh_record(self.user)
        self.user.join('auth_token').execute(self.connection)
        self.assert_(self.user.auth_token is not None)

    def submit_new_password(self, password, password2=None):
        if password2 is None:
            password2 = password
        return self.post_data('/accounts/change-password/%d' % self.user.id,
                data = {'password': password, 'password2': password2})

    def test_send_email(self):
        self.request_auth_token()
        self.assertEquals(len(self.emails), 1)
        self.assertEquals(self.emails[0]['recipient_list'], [self.user.email])
        self.user = self.refresh_record(self.user)
        self.user.join('auth_token').execute(self.connection)
        url = util.make_absolute_url('accounts/change-password?token=' +
                self.user.auth_token.token)
        self.assert_(url in self.emails[0]['body'])

    def page_has_password_form(self, token):
        url = '/accounts/change-password'
        if token:
            response = self.get_page(url, data={'token': token})
        else:
            response = self.get_page(url)
        template = response.template[0].name
        if template == 'guide/bad-auth-token.html':
            return False
        elif template == 'guide/change-password.html':
            return True
        else:
            raise AssertionError("bad template file: " + template)

    def test_password_form_page(self):
        self.assert_(not self.page_has_password_form(token=None))
        self.assert_(not self.page_has_password_form(token='abcdef'))
        self.get_page('/accounts/forgot-password', 
                data={'email': self.user.email})
        self.request_auth_token()
        token = self.user.auth_token.token
        self.assert_(self.page_has_password_form(token=token))
        # token should be deleted now
        self.assert_(not self.page_has_password_form(token=token))

    def test_change_password_permisions(self):
        self.submit_new_password('changetest', 'changetest')
        self.user = self.refresh_record(self.user)
        self.assert_(not self.user.check_password("changetest"))

    def test_change_password(self):
        self.request_auth_token()
        response = self.get_page('/accounts/change-password',
                data={'token': self.user.auth_token.token})
        self.submit_new_password('changetest', 'notthesame')
        self.user = self.refresh_record(self.user)
        self.assert_(not self.user.check_password("changetest"))
        self.submit_new_password('changetest', 'changetest')
        self.connection.commit()
        self.user = self.refresh_record(self.user)
        self.assert_(self.user.check_password("changetest"))
