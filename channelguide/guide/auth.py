from channelguide import util
from models.user import AnonymousUser

SESSION_KEY = 'user'
ADULT_COOKIE_NAME = 'adult_ok'
ADULT_COOKIE_AGE = 60*60*24*365 # 1 year

def login(request, user):
    """Try to log a user in."""

    request.session[SESSION_KEY] = (user.username, user.hashed_password)
    request.session.change_session_key()
    request.user = user
    return True

def logout(request):
    """Logout the currently logged in user."""
    try:
        del request.session[SESSION_KEY]
    except KeyError:
        pass
    request.session.change_session_key()
    request.user = AnonymousUser()

# decorators... pretty much stolen from django code
def user_passes_test(test_func):
    """
    Decorator for views that checks that the user passes the given test,
    redirecting to the log-in page if necessary. The test should be a callable
    that takes the user object and returns True if the user passes.
    """
    def _dec(view_func):
        def _checklogin(request, *args, **kwargs):
            if test_func(request.user):
                return view_func(request, *args, **kwargs)
            return util.send_to_login_page(request)
        _checklogin.__doc__ = view_func.__doc__
        _checklogin.__dict__ = view_func.__dict__

        return _checklogin
    return _dec

login_required = user_passes_test(lambda u: u.is_authenticated())
admin_required = user_passes_test(lambda u: u.is_admin())
supermoderator_required = user_passes_test(lambda u: u.is_supermoderator())
moderator_required = user_passes_test(lambda u: u.is_moderator())

def check_adult(request):
    if request.method == 'GET':
        if request.user.is_authenticated():
            adult_ok = {True: 'yes', False: 'no', None: None}[
                    request.user.adult_ok]
        else:
            adult_ok = request.COOKIES.get(ADULT_COOKIE_NAME, None)
        if adult_ok is None:
            return util.render_to_response(request, 'adult-warning.html')
        elif adult_ok == 'no':
            url = request.META.get('HTTP_REFERER', '/')
            return util.redirect(url)
        else:
            return
    else:
        adult_ok = request.POST.get('adult_ok')
        if adult_ok == 'no':
            url = request.META.get('HTTP_REFERER', '/')
            response = util.redirect(url)
            if request.user.is_authenticated():
                request.user.adult_ok = False
                request.user.save(request.connection)
            else:
                util.set_cookie(response, ADULT_COOKIE_NAME,
                    'no', ADULT_COOKIE_AGE)
        elif adult_ok == 'yes':
            response = util.redirect(request.path)
            if request.user.is_authenticated():
                request.user.adult_ok = True
                request.user.save(request.connection)
            else:
                util.set_cookie(response, ADULT_COOKIE_NAME,
                    'yes', ADULT_COOKIE_AGE)
        else:
            response = util.redirect(request.path)
        return response

def adult_required(view_func):
    """
    Decorator which checks if the user has agreed to see adult channels.
    If they haven't, then they're sent to a warning page.  If they've
    said they don't want to see adult channels, they're redirected back to
    where they came from.
    """
    def _checkadult(request, *args, **kw):
        ca = check_adult(request)
        if ca is not None:
            return ca
        else:
            return view_func(request, *args, **kw)
    _checkadult.__doc__ = view_func.__doc__
    _checkadult.__dict__ = view_func.__dict__
    return _checkadult

