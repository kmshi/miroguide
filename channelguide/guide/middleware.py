import locale
import logging
import traceback
import cStringIO

from channelguide import util, settings
from exceptions import AuthError
from models import Channel, User
from models.user import AnonymousUser
from auth import SESSION_KEY, check_adult
import hotshot, hotshot.stats, tempfile, sys

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
        else:
            req.user = AnonymousUser()
        if isinstance(req.user, AnonymousUser):
            # set adult_ok variable
            req.user.adult_ok = check_adult(req, True)

    def process_exception(self, request, exception):
        if isinstance(exception, AuthError):
            return util.send_to_login_page(request)

class ChannelCountMiddleware(object):
    def process_request(self, request):
        channel_count = Channel.query_approved().count(request.connection)
        request.connection.commit()
        request.total_channels = locale.format('%d', channel_count, True)

class NotificationMiddleware(object):
    """
    NotificationMiddleware adds a add_notification(title, line) method to
    the request.  These notifications will be displayed at the top of the
    page.
    """

    def process_request(self, request):
        request.notifications = []
        request.add_notification = (
                lambda t, l: request.notifications.append((t, l)))

    def process_response(self, request, response):
        if hasattr(request, 'notifications') and request.notifications:
            notification_bar = """<div id="notification-bar">
    <div id="notification-bar-inner">
        <ul>"""
            for (title, line) in request.notifications:
                notification_bar += """
            <li><strong>%s:</strong> %s</li>""" % (title, line)
            notification_bar += """
        </ul>
    </div>
</div>"""
        else:
            notification_bar = ""
        response.content = response.content.replace(
                '<!-- NOTIFICATION BAR -->', notification_bar)
        return response


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



            out = cStringIO.StringIO()

            old_stdout = sys.stdout

            sys.stdout = out



            stats = hotshot.stats.load(self.tmpfile.name)

            #stats.strip_dirs()
            if request.has_key('cumulative'):
                stats.sort_stats('cumulative', 'calls')
            else:
    
                stats.sort_stats('time', 'calls')
            if request.has_key('all'):
                stats.print_stats()
            else:
                stats.print_stats('channelguide/')



            sys.stdout = old_stdout

            stats_str = out.getvalue()



            if response and response.content and stats_str:

                response.content = "<pre>" + stats_str + "</pre>"



        return response

