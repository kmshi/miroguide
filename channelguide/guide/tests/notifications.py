# Copyright (c) 2009 Participatory Culture Foundation
# See LICENSE for details.

from django.http import HttpResponse

from channelguide.testframework import TestCase

class NotificationViewTestCase(TestCase):

    def test_add_notification(self):
        """
        Test that notifications are added when request.add_notification() is called.
        """
        request = self.process_request()
        request.add_notification('title', 'body')
        request.add_notification(None, 'None body')
        self.assertEquals(request.notifications,
                          [('title', 'body'),
                           (None, 'None body')])

    def test_display_notifications(self):
        """
        Test that notifications are displayed when they're added.
        """
        request = self.process_request()
        request.add_notification('title', 'body')
        request.add_notification(None, 'None body')
        response = HttpResponse('<!-- NOTIFICATION BAR -->')
        self.process_response_middleware(request, response)
        self.assertTrue('title' in response.content)
        self.assertTrue('body' in response.content)
        self.assertTrue('None body' in response.content)

    def test_notifications_from_session(self):
        """
        If there is a 'notifications' key in the session, its notifications
        should be added to those added by the view on the next load.
        """
        request = self.process_request()
        request.session.add_notification('session title', 'session body')
        response = HttpResponse('<!-- NOTIFICATION BAR -->')
        self.process_response_middleware(request, response)
        self.assertFalse('session' in response.content)

        cookies = response.cookies
        request = self.process_request(cookies) # next request should show the
                                                # notification
        response = HttpResponse('<!-- NOTIFICATION BAR -->')
        self.process_response_middleware(request, response)
        self.assertTrue('session title' in response.content)
        self.assertTrue('session body' in response.content)

        request = self.process_request(cookies) # third request shouldn't show
                                                # the notification
        response = HttpResponse('<!-- NOTIFICATION BAR -->')
        self.process_response_middleware(request, response)
        self.assertFalse('session title' in response.content)
