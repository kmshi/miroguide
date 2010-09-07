# Copyright (c) 2008-2009 Participatory Culture Foundation
# See LICENSE for details.

import re

from django.core import mail
from django.core.urlresolvers import reverse
from django.conf import settings
from django.contrib.auth.models import User
from django.utils.translation import ugettext as _

from channelguide.testframework import TestCase
from channelguide.cobranding.models import Cobranding

class UserProfileTest(TestCase):
    def setUp(self):
        TestCase.setUp(self)
        self.user = self.make_user('mary')

    def login_data(self):
        return {'username': 'mary', 'password': 'password',
                'which-form': 'login' }

    def register_data(self):
        """
        Return a dictionary of data used to register a new user.
        """
        return {'newusername': u'mike\xf6', 'email': 'mike@mike.com',
                'newpassword': u'password\xdf\xdf',
                'newpassword2': u'password\xdf\xdf',
                'which-form': 'register' }

    def register(self):
        """
        Return the final response from registering a user.
        """
        response = self.post_data("/accounts/register/", self.register_data())
        self.assertRedirect(response, '')
        response = self.get_page('/')
        context = response.context[0]
        self.assertEquals(context['request'].notifications[0][0],
                          _('Thanks for registering!'))
        self.assertEquals(context['user'].username, u'mike\xf6')
        self.assertEquals(context['user'].email, 'mike@mike.com')
        self.assert_(context['user'].check_password(
                u'password\xdf\xdf'))
        self.assertEquals(context['user'].get_profile().user,
                          context['user'])
        self.assertEquals(context['user'].is_active, True)
        return response

    def bad_login_data(self):
        return {'username': 'mary', 'password': 'badpassword',
                'which-form': 'login' }

    def test_login(self):
        response = self.post_data(settings.LOGIN_URL, self.login_data())
        self.assertRedirect(response, '')
        response = self.get_page('/')
        self.assertEquals(response.context[0]['user'].username,
                self.user.username)

    def test_login_with_email(self):
        data = self.login_data()
        data['username'] = self.user.email
        response = self.post_data(settings.LOGIN_URL, data)
        self.assertRedirect(response, '')
        response = self.get_page('/')
        self.assertEquals(response.context[0]['user'].username,
                self.user.username)


    def test_bad_login(self):
        response = self.post_data(settings.LOGIN_URL, self.bad_login_data())
        self.assert_(not response.context[0]['user'].is_authenticated())

    def test_register(self):
        self.register()

    def test_forgot_password(self):
        user = self.make_user('rachel')
        data = {'email': user.email}
        self.post_data("/accounts/password_reset/", data)
        regex = re.compile(r'/accounts/reset/[\w-]+/')
        url = regex.search(mail.outbox[0].body).group(0)

        data = {'new_password1': 'newpass', 'new_password2': 'badmatch'}
        page = self.post_data(url, data=data)
        self.assertEquals(page.status_code, 200) # didn't redirect to a new
                                                 # page

        data['new_password2'] = data['new_password1']
        page = self.post_data(url, data=data)
        self.assertEquals(page.status_code, 302)

        user_check = User.objects.get(pk=user.pk)
        self.assert_(user_check.check_password('newpass'))


    def test_user_starts_unapproved(self):
        """
        Users should start off unapproved.
        """
        response = self.register()
        user = response.context[0]['request'].user
        self.assertEquals(user.get_profile().approved, False)

    def test_registration_send_approval_email(self):
        """
        Registering a user should send an e-mail to that user letting them
        approve their account.
        """
        response = self.register()
        user = response.context[0]['request'].user
        self.check_confirmation_email(user)

    def check_confirmation_email(self, user):
        email = mail.outbox[-1]
        self.assertEquals(email.subject, 'Approve your Miro Guide account')
        self.assertEquals(email.recipients(), ['mike@mike.com'])
        m = re.match("""
You have requested a new user account on Miro Guide and you specified
this address \((.*?)\) as your e-mail address.

If you did not do this, simply ignore this e-mail.  To confirm your
registration, please follow this link:

(.*?)

Your ratings will show up, but won't count towards the average until
you use this confirmation link.

Thanks,
The Miro Guide""", email.body)
        self.assert_(m, 'Email does not match:\n%s' % email.body)
        self.assertEquals(m.groups()[0], 'mike@mike.com')
        self.assertEquals(m.groups()[1],
                '%saccounts/confirm/%s/%s' % (settings.BASE_URL_FULL,
                    user.id, user.get_profile().generate_confirmation_code()))


    def test_confirmation_url_confirms_user(self):
        """
        When the user visits the confirmation url, it should set the approval
        flag to true.
        """
        response = self.register()
        user = response.context[0]['request'].user
        url = user.get_profile().generate_confirmation_url()
        response = self.get_page(url[len(settings.BASE_URL_FULL)-1:])
        user = User.objects.get(pk=user.pk)
        self.assert_(user.get_profile().approved)

    def test_no_confirmation_with_bad_code(self):
        """
        If the user gives an incorrect code, they should not be confirmed.
        """
        response = self.register()
        user = response.context[0]['request'].user
        url = user.get_profile().generate_confirmation_url()
        response = self.get_page(url[len(settings.BASE_URL_FULL)-1:-1])
        user = User.objects.get(pk=user.pk)
        self.assert_(not user.get_profile().approved)

    def test_resend_confirmation_code(self):
        """
        /accounts/confirm/<id>/resend should resent the initial confirmation
        email.
        """
        response = self.register()
        user = response.context[0]['request'].user
        url = user.get_profile().generate_confirmation_url()
        parts = url[len(settings.BASE_URL_FULL)-1:].split('/')
        url = '/'.join(parts[:-1]) + '/resend'
        mail.outbox = []
        response = self.get_page(url)
        self.check_confirmation_email(user)

    def test_unicode_in_data(self):
        """
        The profile page should render even when the user has Unicode elements.
        """
        response = self.register()
        user = response.context[0]['request'].user
        user.city = u'S\u1111o'
        user.save()
        self.get_page(user.get_absolute_url())

class ModerateUserTest(TestCase):
    def setUp(self):
        TestCase.setUp(self)
        self.jane = self.make_user("jane")
        self.jane.is_superuser = True
        self.jane.save()
        self.bob = self.make_user("bob")
        self.cathy = self.make_user("cathy")
        self.adrian = self.make_user("adrian")
        self.judy = self.make_user("judy")
        self.judy.email = 'judy@bob.com'
        self.judy.save()

    def test_auth(self):
        self.login(self.adrian)
        response = self.get_page("/accounts/search", data={'query': 'yahoo'})
        self.assertLoginRedirect(response)
        response = self.post_data("/accounts/profile/",
                {'action': 'promote', 'id': self.bob.id})
        self.assertLoginRedirect(response)
        response = self.post_data("/accounts/profile/",
                {'action': 'demote', 'id': self.bob.id})
        self.assertLoginRedirect(response)

    def check_search(self, query, *correct_results):
        response = self.get_page("/accounts/search", data={'query': query})
        returned_names = [u.username for u in
                          response.context[0]['page'].object_list]
        correct_names = [u.username for u in correct_results]
        self.assertSameSet(returned_names, correct_names)

    def test_search_users(self):
        self.login(self.jane)
        self.check_search('cathy', self.cathy)
        self.check_search('bob', self.bob, self.judy)
        self.check_search('test.test', self.jane, self.bob, self.cathy,
                self.adrian)
        self.check_search('blahblah') # no users should be returned

    def check_promote_demote(self, user, action, permission=None):
        self.post_data("/accounts/profile/%i/" % user.pk, {'action': action})

        user = User.objects.get(pk=user.pk)
        if permission is not None:
            self.assert_(user.has_perm(permission))
        else:
            self.assert_(not user.get_all_permissions())
        return user


    def test_promote_user(self):
        self.login(self.jane)
        user = self.check_promote_demote(self.bob, 'promote',
                                         'user_profile.betatester')
        self.assertFalse(user.has_perm('channels.change_channel'))
        user = self.check_promote_demote(self.bob, 'promote',
                                  'channels.change_channel')
        self.assertFalse(user.has_perm('featured_add_featured_queue'))
        self.check_promote_demote(self.bob, 'promote',
                                  'featured.add_featuredqueue')
        # no group has this permission, so only superusers should have it
        self.check_promote_demote(self.bob, 'promote',
                                  'channels.add_generatedstats')
        self.check_promote_demote(self.bob, 'promote',
                                  'channels.add_generatedstats')

    def test_demote_user(self):
        self.login(self.jane)
        for i in range(5):
            self.cathy.get_profile().promote()
        user = self.check_promote_demote(self.cathy, 'demote',
                                         'featured.add_featuredqueue')
        self.assertFalse(user.is_superuser)
        user = self.check_promote_demote(self.cathy, 'demote',
                                         'channels.change_channel')
        self.assertFalse(user.has_perm('featured.add_featuredqueue'))
        user = self.check_promote_demote(self.cathy, 'demote',
                                         'user_profile.betatester')
        self.assertFalse(user.has_perm('channels.change_channel'))
        user = self.check_promote_demote(self.cathy, 'demote')
        self.assertFalse(user.has_perm('user_profile.betatester'))
        self.check_promote_demote(self.cathy, 'demote')

class EditUserTest(TestCase):
    def setUp(self):
        TestCase.setUp(self)
        self.user = self.make_user('mary')
        self.admin = self.make_user('joe')
        self.admin.is_superuser = True
        self.admin.save()
        self.other_user = self.make_user('bobby',
                                         group='cg_moderator')

    def check_can_see_edit_page(self, user, should_see):
        page = self.get_page('/accounts/profile/%i/' % self.user.id, user)

        if should_see:
            self.assertCanAccess(page)
        else:
            self.assertLoginRedirect(page)

    def test_permissions(self):
        self.check_can_see_edit_page(self.user, True)
        self.check_can_see_edit_page(self.admin, True)
        self.check_can_see_edit_page(self.other_user, False)

class UserViewTest(TestCase):
    def setUp(self):
        TestCase.setUp(self)
        self.user = self.make_user('mary')
        self.channel = self.make_channel(self.user)

    def test_view(self):
        page = self.get_page(self.user.get_profile().get_url())
        self.assertEquals(page.status_code, 200)
        self.assertEquals(page.context['for_user'], self.user)
        self.assertEquals(page.context['cobrand'], None)
        self.assertEquals(page.context['biggest'].paginator.count, 1)
        self.assertEquals(page.context['biggest'].object_list[0], self.channel)

    def test_view_with_site(self):
        site = self.make_channel(self.user)
        site.url = None
        site.save()
        page = self.get_page(self.user.get_profile().get_url())
        self.assertEquals(page.status_code, 200)
        self.assertEquals(page.context['for_user'], self.user)
        self.assertEquals(page.context['cobrand'], None)
        self.assertEquals(page.context['biggest'].paginator.count, 1)
        self.assertEquals(page.context['feed_page'].object_list[0],
                          self.channel)
        self.assertEquals(page.context['site_page'].object_list[0], site)

    def test_url_with_id_is_redirected(self):
        url = reverse('channelguide.user_profile.views.for_user',
                      args=(self.user.pk,))
        page = self.get_page(url)
        self.assertRedirect(page, self.user.get_profile().get_url())

    def test_inactive_user_gives_404(self):
        self.user.is_active = False
        self.user.save()
        page = self.get_page(self.user.get_profile().get_url())
        self.assertEquals(page.status_code, 404)

    def test_unknown_user_gives_404(self):
        url = reverse('channelguide.user_profile.views.for_user',
                      args=('unknown_username',))
        page = self.get_page(url)
        self.assertEquals(page.status_code, 404)

    def test_user_with_cobrand(self):
        cobrand = Cobranding.objects.create(user=self.user)
        page = self.get_page(self.user.get_profile().get_url(),
                             login_as=self.user)
        self.assertEquals(page.context['cobrand'],
                          cobrand)

    def test_user_with_cobrand_admin(self):
        admin = self.make_user('admin')
        admin.is_superuser = True
        admin.save()
        cobrand = Cobranding.objects.create(user=self.user)
        page = self.get_page(self.user.get_profile().get_url(),
                             login_as=admin)
        self.assertEquals(page.context['cobrand'],
                          cobrand)
