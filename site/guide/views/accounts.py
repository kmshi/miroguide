from django.http import HttpResponseRedirect
from django.utils.translation import gettext as _
import django.newforms as forms

from channelguide.auth import logout, login
from channelguide.auth.decorators import moderator_required
from channelguide.auth.models import User
from channelguide.templatehelpers import Pager
from channelguide import util
from forms import LoginForm, RegisterForm

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
    login_form = LoginForm(request.db_session, login_data)
    register_form = RegisterForm(request.db_session, register_data)
    if login_form.is_valid():
        login(request, login_form.clean_data['user'])
        return util.redirect(next)
    elif register_form.is_valid():
        login(request, register_form.clean_data['user'])
        return util.redirect(next)
    return util.render_to_response(request, 'accounts/login.html', { 
        'next' : request.GET.get('next'),
        'login_form': login_form,
        'register_form': register_form,
        'message': message,
    })

def logout_view(request):
    logout(request)
    return HttpResponseRedirect('/')

class NewUserField(forms.CharField):
    def clean(self, value):
        rv = super(NewUserField, self).clean(value)
        if self.db_session.query(User).get_by(username=value):
            raise forms.ValidationError(_("username already taken"))
        return rv

class NewEmailField(forms.EmailField):
    def clean(self, value):
        rv = super(NewEmailField, self).clean(value)
        if self.db_session.query(User).get_by(email=value):
            raise forms.ValidationError(_("email already taken"))
        return rv

class CreateUserForm(forms.Form):
    username = NewUserField(max_length=25)
    email = NewEmailField(max_length=100)
    password = forms.CharField(max_length=30, widget=forms.PasswordInput)
    password2 = forms.CharField(max_length=30, widget=forms.PasswordInput,
            label=_("Confirm Password"))

    def __init__(self, db_session, data=None):
        super(CreateUserForm, self).__init__(data)
        self.fields['email'].db_session = db_session
        self.fields['username'].db_session = db_session

    def clean(self):
        if (self.data['password'] and self.data['password2'] and
                self.data['password'] != self.data['password2']):
            raise forms.ValidationError(_("Passwords don't match"))
        return super(CreateUserForm, self).clean()

    def save_user(self, db_session):
        u = User()
        u.username = self.clean_data['username']
        u.email = self.clean_data['email']
        u.set_password(self.clean_data['password'])
        db_session.save(u)
        return u

def create_user(request):
    if request.method != 'POST':
        form = CreateUserForm(request.db_session)
    else:
        form = CreateUserForm(request.db_session, request.POST)
        if form.is_valid():
            form.save_user(request.db_session)
            return util.redirect("accounts/after-create")
    return util.render_to_response(request, 'accounts/create.html', 
            {'form': form})

def after_create(request):
    return util.render_to_response(request, 'accounts/after_create.html')

def user(request, id):
    query = request.db_session.query(User)
    user = util.get_object_or_404(query, id)
    action = request.POST.get('action')
    if action == 'promote':
        request.user.check_is_admin()
        user.promote()
    elif action == 'demote':
        request.user.check_is_admin()
        user.demote()
    return util.redirect_to_referrer(request)

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

    return util.render_to_response(request, 'accounts/search.html', {
        'query': query,
        'pager': pager,
        'results': results,
    })

@moderator_required
def moderators(request):
    q = request.db_session.query(User, order_by=User.c.username)
    select = q.select().filter(User.c.role.in_(*User.ALL_MODERATOR_ROLES))
    pager =  Pager(15, select, request)
    return util.render_to_response(request, 'accounts/moderators.html', {
        'moderators': pager.items,
        'pager': pager,
    })
