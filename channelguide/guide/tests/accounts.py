import re 

from django.conf import settings

from channelguide import util
from channelguide.guide.models import User
from channelguide.testframework import TestCase

class AccountTest(TestCase):
    def setUp(self):
        TestCase.setUp(self)
        self.user = self.make_user('mary')

    def login_data(self):
        return {'username': 'mary', 'password': 'password',
                'which-form': 'login' }

    def register_data(self):
        return {'username': 'mike', 'email': 'mike@mike.com',
                'password': 'password', 'password2': 'password',
                'which-form': 'register' }

    def bad_login_data(self):
        return {'username': 'mary', 'password': 'badpassword',
                'which-form': 'login' }

    def test_login(self):
        response = self.post_data("/accounts/login", self.login_data())
        self.assertRedirect(response, '')
        response = self.get_page('/front')
        self.assertEquals(response.context[0]['user'].username,
                self.user.username)

    def test_bad_login(self):
        response = self.post_data("/accounts/login", self.bad_login_data())
        self.assert_(not response.context[0]['user'].is_authenticated())

    def test_register(self):
        response = self.post_data("/accounts/login", self.register_data())
        self.assertRedirect(response, '')
        response = self.get_page('/front')
        self.assertEquals(response.context[0]['user'].username, 'mike')
        self.assertEquals(response.context[0]['user'].email, 'mike@mike.com')
        self.assert_(response.context[0]['user'].check_password('password'))

    def test_forgot_password(self):
        user = self.make_user('rachel')
        data = {'email': user.email}
        response = self.post_data("/accounts/forgot-password", data)
        regex = re.compile(r'/accounts/change-password\?token=(\w+)')
        token = regex.search(self.emails[0]['body']).group(1)
        data = {'token': token}
        page =  self.get_page('/accounts/change-password', data=data)

        data = {'password': 'newpass', 'password2': 'badmatch'}
        page = self.post_data('/accounts/change-password/%d' % user.id, 
                data=data)
        data = {'password': 'newpass', 'password2': 'newpass'}
        self.post_data('/accounts/change-password/%d' % user.id, data=data)
        user_check = User.get(self.connection, user.id)
        self.assertEquals(user_check.hashed_password, 
                util.hash_string('newpass'))

class ModerateUserTest(TestCase):
    def setUp(self):
        TestCase.setUp(self)
        self.jane = self.make_user("jane", role=User.ADMIN)
        self.bob = self.make_user("bob")
        self.cathy = self.make_user("cathy")
        self.adrian = self.make_user("adrian")
        self.judy = self.make_user("judy")
        self.judy.email = 'judy@bob.com'
        self.save_to_db(self.judy)

    def test_auth(self):
        self.login(self.adrian)
        response = self.get_page("/accounts/search", data={'query': 'yahoo'})
        self.assertLoginRedirect(response)
        response = self.post_data("/accounts/%d" % self.bob.id, 
                {'action': 'promote'})
        self.assertLoginRedirect(response)
        response = self.post_data("/accounts/%d" % self.bob.id, 
                {'action': 'demote'})
        self.assertLoginRedirect(response)

    def check_search(self, query, *correct_results):
        response = self.get_page("/accounts/search", data={'query': query})
        returned_names = [u.username for u in response.context[0]['results']]
        correct_names = [u.username for u in correct_results]
        self.assertSameSet(returned_names, correct_names)

    def test_search_users(self):
        self.login(self.jane)
        self.check_search('cathy', self.cathy)
        self.check_search('bob', self.bob, self.judy)
        self.check_search('pculture.org', self.jane, self.bob, self.cathy,
                self.adrian)
        self.check_search('blahblah') # no users should be returned

    def check_promote_demote(self, user, action, new_role):
        self.connection.commit()
        self.post_data("/accounts/%d" % user.id, {'action': action})
        user = self.refresh_record(user)
        self.assertEquals(user.role, new_role)

    def test_promote_user(self):
        self.login(self.jane)
        self.check_promote_demote(self.bob, 'promote', User.MODERATOR)
        self.check_promote_demote(self.bob, 'promote', User.SUPERMODERATOR)
        self.check_promote_demote(self.bob, 'promote', User.ADMIN)
        self.check_promote_demote(self.bob, 'promote', User.ADMIN)

    def test_demote_user(self):
        self.login(self.jane)
        self.cathy.role = User.ADMIN
        self.cathy.save(self.connection)
        self.check_promote_demote(self.cathy, 'demote', User.SUPERMODERATOR)
        self.check_promote_demote(self.cathy, 'demote', User.MODERATOR)
        self.check_promote_demote(self.cathy, 'demote', User.USER)
        self.check_promote_demote(self.cathy, 'demote', User.USER)

class EditUserTest(TestCase):
    def setUp(self):
        TestCase.setUp(self)
        self.user = self.make_user('mary')
        self.admin = self.make_user('joe', role=User.ADMIN)
        self.other_user = self.make_user('bobby', role=User.MODERATOR)

    def check_can_see_edit_page(self, user, should_see):
        self.login(user)
        url = '/accounts/%d' % self.user.id
        if should_see:
            self.assertCanAccess(url)
        else:
            self.assertLoginRedirect(url)

    def test_permissions(self):
        self.check_can_see_edit_page(self.user, True)
        self.check_can_see_edit_page(self.admin, True)
        self.check_can_see_edit_page(self.other_user, False)
