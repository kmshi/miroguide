import logging
import traceback

from models import User, AnonymousUser
from channelguide import util
from channelguide.auth import SESSION_KEY, AuthError

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
            users = req.db_session.query(User).select_by(username=username)[:1]
            if users and users[0].hashed_password == password:
                req.user = users[0]
            else:
                req.user = AnonymousUser()
        else:
            req.user = AnonymousUser()

    def process_exception(self, request, exception):
        if isinstance(exception, AuthError):
            return util.send_to_login_page(request)
