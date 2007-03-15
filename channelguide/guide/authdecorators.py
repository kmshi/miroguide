from django.conf import settings
from channelguide import util

# pretty much stolen from django code
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
