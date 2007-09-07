import locale
import logging
import traceback

from channelguide import util, settings
from exceptions import AuthError
from models import Channel, User
from models.user import AnonymousUser
from auth import SESSION_KEY
import hotshot, hotshot.stats, tempfile, StringIO, sys
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

class ProfileMiddleware(object):

    """

    Displays hotshot profiling for any view.

    http://yoursite.com/yourview/?prof



    Add the "prof" key to query string by appending ?prof (or &prof=)

    and you'll see the profiling results in your browser.

    It's set up to only be available in django's debug mode,

    but you really shouldn't add this middleware to any production configuration.

    * Only tested on Linux

    """

    def process_request(self, request):

        if request.has_key('prof'):

            self.tmpfile = tempfile.NamedTemporaryFile()

            self.prof = hotshot.Profile(self.tmpfile.name)



    def process_view(self, request, callback, callback_args, callback_kwargs):

        if request.has_key('prof'):

            return self.prof.runcall(callback, request, *callback_args, **callback_kwargs)



    def process_response(self, request, response):

        if request.has_key('prof'):

            self.prof.close()



            out = StringIO.StringIO()

            old_stdout = sys.stdout

            sys.stdout = out



            stats = hotshot.stats.load(self.tmpfile.name)

            #stats.strip_dirs()

            stats.sort_stats('cumulative', 'calls')

            stats.print_stats('channelguide/')



            sys.stdout = old_stdout

            stats_str = out.getvalue()



            if response and response.content and stats_str:

                response.content = "<pre>" + stats_str + "</pre>"



        return response

