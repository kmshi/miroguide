# Copyright (c) 2008 Participatory Culture Foundation
# See LICENSE for details.

from django.core.paginator import Paginator
from django.http import HttpResponseRedirect
from django.utils.translation import gettext as _

from channelguide import util
from channelguide.guide.auth import logout, login, moderator_required, login_required
from channelguide.guide.exceptions import AuthError
from channelguide.guide.forms import user as user_forms
from channelguide.guide.models import User, UserAuthToken, Rating, Channel
from channelguide.guide.templateutil import QueryObjectList

def get_login_message(next_url):
    if "channels/submit" in next_url:
        header = _("List Your Channel in the Miro Guide!")
        body = _("All you need is an account...")
        return '<h1>%s</h1>%s' % (header, body)
    else:
        title = _("Rate Channels, Get Recommendations")
        line1 = _("Sign in (or create an account)")
        line2 = _("Give Channels Star Ratings")
        line3 = _("We'll Give You Recommendations")
        return """<h1>%s</h1>
<ol>
<li>%s</li>
<li>%s</li>
<li>%s</li>
</ol>""" % (title, line1, line2, line3)

def get_register_message(next_url):
    if "channels/submit" not in next_url:
        return """<div class="info">%s</div>""" % _("Your ratings will show up, but won't count towards the average until you confirm your e-mail.")
    else:
        return ""

def get_login_additional(next_url):
    if "channels/submit" in next_url:
        return """<div>
<h1>%s</h1>
<img id="registration2" src="/images/registration2.jpg" />
%s
</div>
<div class="clear"></div>""" % (
    _("Your Video RSS Feed is a Miro Channel"),
    _("It is super easy to submit your channel to the Miro Guide. Just give us the feed address, answer a few easy questions, and you&apos;re all done."))
    else:
        return """<div>
<h1>%s</h1>
<img id="registration1" src="/images/registration1.jpg" />
%s
</div>
<div>
<h1>%s</h1>
<img id="registration2" src="/images/registration2.jpg" />
%s
</div>""" % (
        _("Why Should I Rate Channels?"),
        _("We are giving personalized recommendations, based on what you do and don't like. If you've ever used Netflix&reg;, you already know what we're talking about here. The more you rate, the more accurately we can recommend channels to you. It&apos;s that simple!"),
        _("A Completely Open Guide"),
        _("Because we accept channels (RSS feeds, aka 'video podcasts') from anyone, the Miro Guide is constantly expanding. Channel creators can add their feeds freely. If you know of a great video podcast that isn&apos;t already in the Guide, please contact the creator and ask them to submit it.")
        )
def login_view(request):
    next = request.GET.get('next')
    if next is None:
        next = request.POST.get('next')
    if next is None:
        next = request.META.get('HTTP_REFERER')
    if next is None:
        next = ''
    login_data = register_data = None
    message = '' # only show messages before the user submits a form
    if request.POST.get('which-form') == 'login':
        login_data = request.POST
    elif request.POST.get('which-form') == 'register':
        register_data = request.POST
    else:
        message = util.mark_safe(get_login_message(next))
    register_message = util.mark_safe(get_register_message(next))
    additional = util.mark_safe(get_login_additional(next))
    login_form = user_forms.LoginForm(request.connection, login_data)
    register_form = user_forms.RegisterForm(request.connection, register_data)
    if login_form.is_valid():
        login(request, login_form.get_user())
        return util.redirect(next)
    elif register_form.is_valid():
        try:
            user = register_form.make_user()
        except Exception:
            # check again, it's probably a duplicate user
            register_form.full_clean()
        else:
            login(request, user)
            return util.redirect(next)
    return util.render_to_response(request, 'login.html', { 
        'next' : next,
        'login_form': login_form,
        'register_form': register_form,
        'register_message': register_message,
        'message': message,
        'additional': additional,
    })

def logout_view(request):
    logout(request)
    return HttpResponseRedirect('/')

def user(request, id):
    query = User.query().join('channels')
    user = util.get_object_or_404(request.connection, query, id)
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

@login_required
def confirm(request, id, code):
    """
    A user is trying to confirm their account.
    """
    user = util.get_object_or_404(request.connection, User.query(), id)
    if user.id != request.user.id and not request.user.is_admin():
        raise AuthError('must be logged in as the same user')
    userApproved = False
    if user.generate_confirmation_code() == code:
        userApproved = True
        user.approved = True
        user.blocked = False
        user.save(request.connection)
        for rating in Rating.query().where(user_id=user.id).execute(request.connection):
            if rating.rating is not None:
                channel = Channel.query().join(
                        'rating').get(request.connection,
                            rating.channel_id)
                channel.rating.count += 1
                channel.rating.total += rating.rating
                channel.rating.average = float(channel.rating.total) / channel.rating.count
                channel.rating.save(request.connection)
        if request.user.id == user.id:
            request.user = user # so it doesn't do the warning bar
        form = None
    else:
        if request.method == 'POST':
            form = user_forms.ConfirmationEmailRequestForm(request.connection,
                data=request.POST)
            if form.is_valid():
                if form.cleaned_data['email']:
                    user.email = form.cleaned_data['email']
                    user.save(request.connection)
                form = None
        else:
            form = user_forms.ConfirmationEmailRequestForm(request.connection)
            form.fields['email'].initial = user.email
        if code == "resend":
            user.send_confirmation_email()
    return util.render_to_response(request, 'confirm.html', {
            'approved': userApproved,
            'form' : form,
            'code': code})

def edit_user_form(request, user):
    if request.user.id != user.id:
        request.user.check_is_admin()
    if user.is_moderator():
        FormClass = user_forms.EditModeratorForm
    elif user.channels:
        FormClass = user_forms.EditChannelOwnerForm
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
        'for_user':user,
        'form': form})

@moderator_required
def search(request):
    query = request.GET.get('query', '')
    if not query:
        results = []
        page = None
    else:
        criteria = '%%%s%%' % query
        user_query = User.query(User.c.username.like(criteria) |
                User.c.email.like(criteria))
        paginator = Paginator(QueryObjectList(request.connection,
                                              user_query), 10)
        page = paginator.page(request.GET.get('page', 1))

    return util.render_to_response(request, 'user-search.html', {
        'query': query,
        'page': page,
    })

@moderator_required
def moderators(request):
    query = User.query(User.c.role.in_(User.ALL_MODERATOR_ROLES))
    query.order_by('username')
    paginator = Paginator(QueryObjectList(request.connection, query), 15)
    page = paginator.page(request.GET.get('page', 1))
    return util.render_to_response(request, 'moderators.html', {
        'page': page,
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
