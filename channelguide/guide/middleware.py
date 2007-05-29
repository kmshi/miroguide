import locale
import logging
import traceback

from channelguide import util
from exceptions import AuthError
from models import Channel, User
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
                req.connection.commit()
        else:
            req.user = AnonymousUser()

    def process_exception(self, request, exception):
        if isinstance(exception, AuthError):
            return util.send_to_login_page(request)

class ChannelCountMiddleware(object):
    def process_request(self, request):
        channel_count = Channel.query_approved().count(request.connection)
        request.connection.commit()
        request.total_channels = locale.format('%d', channel_count, True)

