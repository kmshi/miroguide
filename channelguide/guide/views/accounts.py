from django.http import HttpResponseRedirect
from django.utils.translation import gettext as _
import django.newforms as forms

from channelguide import util
from channelguide.guide.auth import logout, login, moderator_required
from channelguide.guide.forms import user as user_forms
from channelguide.guide.models import User, UserAuthToken
from channelguide.guide.templateutil import Pager

def get_login_message(next_url):
    if next_url.startswith("channels/submit"):
        return _("""To submit a channel to the guide, you must \
first login to your account.  If you don't have an account, make one below. \
It's free and only takes 30 seconds to create.""")

def login_view(request):
    next = request.GET.get('next')
    if next is None:
        next = request.POST.get('next')
    if next is None:
        next = ''

    login_data = register_data = None
    message = '' # only show messages before the user submits a form
    if request.POST.get('which-form') == 'login':
        login_data = request.POST
    elif request.POST.get('which-form') == 'register':
        register_data = request.POST
    else:
        message = get_login_message(next)
    login_form = user_forms.LoginForm(request.connection, login_data)
    register_form = user_forms.RegisterForm(request.connection, register_data)
    if login_form.is_valid():
        login(request, login_form.get_user())
        return util.redirect(next)
    elif register_form.is_valid():
        login(request, register_form.make_user())
        return util.redirect(next)
    return util.render_to_response(request, 'login.html', { 
        'next' : request.GET.get('next'),
        'login_form': login_form,
        'register_form': register_form,
        'message': message,
    })

def logout_view(request):
    logout(request)
    return HttpResponseRedirect('/')

def user(request, id):
    user = util.get_object_or_404(request.connection, User, id)
    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'promote':
            request.user.check_is_admin()
            user.promote()
            user.save(request.connection)
        elif action == 'demote':
            request.user.check_is_admin()
            user.demote()
            user.save(request.connection)
        elif action == 'edit':
            return edit_user_form(request, user)
        return util.redirect_to_referrer(request)
    else:
        return edit_user_form(request, user)

def edit_user_form(request, user):
    if request.user.id != user.id:
        request.user.check_is_admin()
    if user.is_moderator():
        FormClass = user_forms.EditModeratorForm
    else:
        FormClass = user_forms.EditUserForm

    if request.method == 'POST':
        form = FormClass(request.connection, user, request.POST)
        if form.is_valid():
            form.update_user()
            if user is request.user:
                login(request, user) # needed to handle password changes
            return util.redirect(user.get_absolute_url())
    else:
        form = FormClass(request.connection, user)
    return util.render_to_response(request, 'edit-user.html', {
        'form': form})

@moderator_required
def search(request):
    query = request.GET.get('query', '')
    if not query:
        results = []
        pager = None
    else:
        criteria = '%%%s%%' % query
        user_query = User.query(User.c.username.like(criteria) |
                User.c.email.like(criteria))
        pager =  Pager(10, user_query, request)
        results = pager.items

    return util.render_to_response(request, 'user-search.html', {
        'query': query,
        'pager': pager,
        'results': results,
    })

@moderator_required
def moderators(request):
    query = User.query(User.c.role.in_(User.ALL_MODERATOR_ROLES))
    query.order_by('username')
    pager =  Pager(15, query, request)
    return util.render_to_response(request, 'moderators.html', {
        'moderators': pager.items,
        'pager': pager,
    })

def forgot_password(request):
    form = util.create_post_form(user_forms.AuthTokenRequestForm, request)
    if form.is_valid():
        email=form.cleaned_data['email']
        query = User.query(email=email).join("auth_token")
        user = query.get(request.connection)
        user.make_new_auth_token(request.connection)
        user.auth_token.send_email()
        return util.redirect("accounts/auth-token-sent", {'email': email})
    else:
        return util.render_to_response(request, 'auth-token-request.html', {
            'form': form,
        })

def auth_token_sent(request):
    return util.render_to_response(request, 'auth-token-sent.html', {
            'email': request.GET.get('email')
        })

def change_password(request):
    token = request.GET.get("token")
    db_token = UserAuthToken.find_token(request.connection, token)
    if db_token is not None:
        db_token.join("user").execute(request.connection)
        login(request, db_token.user)
        db_token.delete(request.connection)
        form = user_forms.ChangePasswordForm(request.connection)
        return util.render_to_response(request, 'change-password.html', { 
            'form': form,
        })
    else:
        return util.render_to_response(request, 'bad-auth-token.html')

def change_password_submit(request, id):
    user = util.get_object_or_404(request.connection, User, id)
    request.user.check_same_user(user)
    form = user_forms.ChangePasswordForm(request.connection, request.POST)
    if form.is_valid():
        user.set_password(form.cleaned_data['password'])
        user.save(request.connection)
        login(request, user) # needed to handle password changes
        return util.redirect('accounts/password-changed')
    return util.render_to_response(request, 'change-password.html', { 
        'form': form,
    })

def password_changed(request):
    return util.render_to_response(request, 'password-changed.html')
