# Copyright (c) 2008-2009 Participatory Culture Foundation
# See LICENSE for details.

import socket
from channelguide.testframework import TestCase
from channelguide import util
from django.core import mail

class EmailTestCase(TestCase):

    def _raise_socket_error(self, *args, **kw):
        raise socket.timeout

    def setUp(self):
        TestCase.setUp(self)
        self.old_send = mail.SMTPConnection.send_messages
        mail.SMTPConnection.send_messages = self._raise_socket_error

    def tearDown(self):
        mail.SMTPConnection.send_messages = self.old_send

    def test_send_mail_ignores_error(self):
        """
        If there's a socket error when sending an e-mail, we should just
        ignore it.
        """
        util.send_mail("Hello", "World", "test@test.com", ["test@test.com"])
