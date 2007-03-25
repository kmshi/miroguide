from django.http import HttpResponseRedirect
from django.utils.translation import gettext as _
import django.newforms as forms

from channelguide import util
from channelguide.guide.auth import logout, login, moderator_required
from channelguide.guide.forms import user as user_forms
from channelguide.guide.models import User
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
    login_form = user_forms.LoginForm(request.db_session, login_data)
    register_form = user_forms.RegisterForm(request.db_session, register_data)
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
    query = request.db_session.query(User)
    user = util.get_object_or_404(query, id)
    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'promote':
            request.user.check_is_admin()
            user.promote()
        elif action == 'demote':
            request.user.check_is_admin()
            user.demote()
        elif action == 'edit':
            return edit_user_form(request, user)
        return util.redirect_to_referrer(request)
    else:
        return edit_user_form(request, user)

def edit_user_form(request, user):
    if request.user is user:
        request.user.check_is_admin()
    if request.method == 'POST':
        form = user_forms.EditUserForm(request.db_session, user, request.POST)
        if form.is_valid():
            form.update_user()
            if user is request.user:
                login(request, user) # needed to handle password changes
            return util.redirect(user.get_absolute_url())
    else:
        form = user_forms.EditUserForm(request.db_session, user)
    return util.render_to_response(request, 'edit-user.html', {
        'form': form})

@moderator_required
def search(request):
    query = request.GET.get('query', '')
    if not query:
        results = []
        pager = None
    else:
        q = request.db_session.query(User)
        criteria = '%%%s%%' % query
        select = q.select(User.c.username.like(criteria) |
                User.c.email.like(criteria))
        pager =  Pager(10, select, request)
        results = pager.items

    return util.render_to_response(request, 'user-search.html', {
        'query': query,
        'pager': pager,
        'results': results,
    })

@moderator_required
def moderators(request):
    q = request.db_session.query(User, order_by=User.c.username)
    select = q.select().filter(User.c.role.in_(*User.ALL_MODERATOR_ROLES))
    pager =  Pager(15, select, request)
    return util.render_to_response(request, 'moderators.html', {
        'moderators': pager.items,
        'pager': pager,
    })

@moderator_required
def moderator_board_emails(request, id):
    query = request.db_session.query(User)
    user = util.get_object_or_404(query, id)
    user.moderator_board_emails = (request.POST.get('set-to') == 'enable')
    return util.redirect('moderate')

def status_emails(request, id):
    query = request.db_session.query(User)
    user = util.get_object_or_404(query, id)
    user.status_emails = (request.POST.get('set-to') == 'enable')
    return util.redirect('moderate')
