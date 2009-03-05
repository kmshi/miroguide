# Copyright (c) 2008 Participatory Culture Foundation
# See LICENSE for details.

import logging
import traceback

from channelguide import util
from exceptions import AuthError
from models import User
from models.user import AnonymousUser
from auth import SESSION_KEY

class UserMiddleware(object):
    """Add a User object to each request.

    Catch AuthError exceptions and redirect the user to the login page.
    """

    def process_request(self, req):
        if SESSION_KEY in req.session:
            try:
                username, password = req.session[SESSION_KEY]
            except:
                logging.warn("Error reading user session info:")
                logging.warn(traceback.format_exc())
                del req.session[SESSION_KEY]
                req.user = AnonymousUser()
                return
            query = User.query(username=username, hashed_password=password)
            query.join("channels")
            try:
                req.user = query.get(req.connection)
            except LookupError:
                req.user = AnonymousUser()
            else:
                if req.user.approved == 0:
                    req.add_notification('Welcome', 'You are now logged in!  Click into any channel to give it a star rating.')
                    req.add_notification('Confirm', """Confirm your e-mail to make your ratings count towards the average.  <a href="/accounts/confirm/%i/resend">Didn't get the e-mail?</a>""" % req.user.id)

                req.connection.commit()
                if req.user.is_authenticated() and req.user.language:
                    req.session['django_language'] = req.user.language
        else:
            req.user = AnonymousUser()

    def process_exception(self, request, exception):
        if isinstance(exception, AuthError):
            return util.send_to_login_page(request)

    def process_response(self, request, response):
        if hasattr(request, 'connection') and hasattr(request, 'user') and request.user.is_authenticated():
            if (request.session.get('django_language')
                   and request.user.language != request.session['django_language']):
                request.user.language = request.session['django_language']
                request.user.save(request.connection)
        return response

class NotificationMiddleware(object):
    """
    NotificationMiddleware adds a add_notification(title, line) method to
    the request.  These notifications will be displayed at the top of the
    page.
    """

    def process_request(self, request):
        if hasattr(request, 'session') and 'notifications' in request.session:
            request.notifications = request.session.pop('notifications')
        else:
            request.notifications = []
        request.add_notification = (
                lambda t, l: request.notifications.append((t, l)))

    def process_response(self, request, response):
        if hasattr(request, 'notifications') and request.notifications:
            notification_bar = """<div id="notification-bar">
    <div id="notification-bar-inner">
        <ul>"""
            for (title, line) in request.notifications:
                if title is not None:
                    notification_bar += """
            <li><strong>%s:</strong> %s</li>""" % (title.encode('utf8'),
                                                   line.encode('utf8'))
                else:
                    notification_bar += """
            <li>%s</li>""" % line.encode('utf8')
            notification_bar += """
        </ul>
    </div>
</div>"""
        else:
            notification_bar = ""
        response.content = response.content.replace(
                '<!-- NOTIFICATION BAR -->', notification_bar)
        return response
