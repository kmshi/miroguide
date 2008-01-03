import socket
from channelguide.testframework import TestCase
from channelguide import util

class EmailTestCase(TestCase):

    def _raise_socket_error(self, *args, **kw):
        raise socket.timeout

    def setUp(self):
        TestCase.setUp(self)
        util.emailer = self._raise_socket_error

    def test_send_mail_ignores_error(self):
        """
        If there's a socket error when sending an e-mail, we should just
        ignore it.
        """
        util.send_mail("Hello", "World", "test@test.com", ["test@test.com"])
import socket
from channelguide.testframework import TestCase
from channelguide import util

class EmailTestCase(TestCase):

    def _raise_socket_error(self, *args, **kw):
        raise socket.timeout

    def setUp(self):
        TestCase.setUp(self)
        util.emailer = self._raise_socket_error

    def test_send_mail_ignores_error(self):
        """
        If there's a socket error when sending an e-mail, we should just
        ignore it.
        """
        util.send_mail("Hello", "World", "test@test.com", ["test@test.com"])
