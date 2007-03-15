SESSION_KEY = 'user'

class AuthError(Exception):
    pass

def login(request, user):
    """Try to log a user in."""
    request.session[SESSION_KEY] = (user.username, user.hashed_password)
    request.user = user
    return True

def logout(request):
    """Logout the currently logged in user."""
    try:
        del request.session[SESSION_KEY]
    except KeyError:
        pass
    from models import AnonymousUser
    request.user = AnonymousUser()
