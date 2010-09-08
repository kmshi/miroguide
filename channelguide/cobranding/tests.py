# Copyright (c) 2008 Participatory Culture Foundation
# See LICENSE for details.

from channelguide.cobranding.models import Cobranding
from channelguide.testframework import TestCase

class CobrandingTestCase(TestCase):

    def setUp(self):
        TestCase.setUp(self)
        self.admin = self.make_user('admin')
        self.admin.is_superuser = True
        self.admin.save()
        self.user = self.make_user('user')
        self.plain = self.make_user('plain')
        self.channels = []
        for i in range(3):
            channel = self.make_channel(self.user, state='A')
            self.channels.append(channel)

    def test_admin_can_create_cobrand(self):
        self.assertRaises(Cobranding.DoesNotExist,
                          Cobranding.objects.get, user='user')
        self.get_page('/cobranding/admin/user', self.admin)
        Cobranding.objects.get(user='user')

    def test_user_cannot_create_cobrand(self):
        page = self.get_page('/cobranding/admin/user', self.user)
        self.assertEquals(page.status_code, 404)

    def test_regular_cannot_edit_cobrand(self):
        self.get_page('/cobranding/admin/user', self.admin)
        self.assertLoginRedirect(self.get_page('/cobranding/admin/user',
            self.plain))

    def test_admin_can_change_cobrand(self):
        names = ('html_title', 'page_title', 'url', 'icon_url', 'description',
                'link1_url', 'link1_text', 'link2_url', 'link2_text',
                'link3_url', 'link3_text')
        post_data = {}
        for name in names:
            post_data[name] = name
        self.get_page('/cobranding/admin/user', self.admin)
        cb = Cobranding.objects.get(user='user')
        response = self.post_data(cb.get_admin_url(), post_data, self.admin)
        self.assertEquals(response.status_code, 200)
        cb = Cobranding.objects.get(pk=cb.pk)
        for name in names:
            self.assertEquals(getattr(cb, name), name)

    def test_blanks_are_none(self):
        self.get_page('/cobranding/admin/user', self.admin)
        names = ('link1_url', 'link1_text', 'link2_url',
                'link2_text', 'link3_url', 'link3_text')
        post_data = {'html_title': 'user', 'page_title': 'user', 'url': 'user',
                'description': 'user', 'icon_url': 'user'}
        for name in names:
            post_data[name] = u'foo'
        self.post_data('/cobranding/admin/user', post_data, self.admin)
        cb = Cobranding.objects.get(user='user')
        for name in names:
            self.assertEquals(getattr(cb, name), 'foo')
            post_data[name] = u''
        self.post_data('/cobranding/admin/user', post_data, self.admin)
        cb = Cobranding.objects.get(user='user')
        for name in names:
            self.assert_(getattr(cb, name) is None)

    def test_view_cobrand(self):
        self.get_page('/cobranding/admin/user', self.admin)
        cobrand = Cobranding.objects.get(user='user')
        response = self.get_page(cobrand.get_url())
        self.assertEquals(response.status_code, 200)
        self.assertEquals(response.context['cobrand'],
                          cobrand)

    def test_view_unknown_cobrand(self):
        response = self.get_page('/cobranding/user')
        self.assertEquals(response.status_code, 404)
