# Copyright (c) 2008 Participatory Culture Foundation
# See LICENSE for details.

from channelguide.guide.models import Cobranding
from channelguide.testframework import TestCase

class CobrandingAdminTestCase(TestCase):

    def setUp(self):
        TestCase.setUp(self)
        self.admin = self.make_user('admin', role='A')
        self.user = self.make_user('user')
        self.plain = self.make_user('plain')
        self.channels = []
        for i in range(3):
            channel = self.make_channel(self.user, state='A')
            self.channels.append(channel)

    def test_admin_can_create_cobrand(self):
        self.assertRaises(Exception,  Cobranding.get, self.connection, 'user')
        self.get_page('/cobranding/admin/user', self.admin)
        self.refresh_connection()
        Cobranding.get(self.connection, 'user')

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
        self.post_data('/cobranding/admin/user', post_data, self.admin)
        self.refresh_connection()
        cb = Cobranding.get(self.connection, 'user')
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
        self.refresh_connection()
        cb = Cobranding.get(self.connection, 'user')
        for name in names:
            self.assertEquals(getattr(cb, name), 'foo')
            post_data[name] = u''
        self.post_data('/cobranding/admin/user', post_data, self.admin)
        self.refresh_connection()
        cb = Cobranding.get(self.connection, 'user')
        for name in names:
            self.assert_(getattr(cb, name) is None)
