# Copyright (c) 2008-2009 Participatory Culture Foundation
# See LICENSE for details.

from django.conf import settings
from django.contrib.auth import login
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.models import User, Group
from django.contrib.auth.decorators import permission_required, login_required
from django.contrib.auth.views import redirect_to_login
from django.core.paginator import Paginator, InvalidPage
from django.db.models import Q
from django.http import Http404
from django.shortcuts import get_object_or_404, render_to_response
from django.template.context import RequestContext
from django.utils.translation import gettext as _

from channelguide import util
from channelguide.user_profile.models import UserProfile
from channelguide.user_profile import forms as user_forms
from channelguide.labels.models import Language
from channelguide.cobranding.models import Cobranding

def register_view(request):
    next = request.GET.get('next')
    if next is None:
        next = request.POST.get('next')
    if next is None:
        next = request.META.get('HTTP_REFERER')
    if next is None:
        next = ''
    register_form = user_forms.RegisterForm(request.POST)
    if register_form.is_valid():
        #try:
            user = register_form.make_user()
        #except User.:
        #    # check again, it's probably a duplicate user
        #    register_form.full_clean()
        #else:
            login(request, user)
            request.session['notifications'] = [(_('Thanks for registering!'),
                                                 _("We've sent a confirmation "
                                                   "e-mail to the address you "
                                                   "provided."))]
            return util.redirect(next)
    return render_to_response('registration/login.html', {
        'next' : next,
        'login_form': AuthenticationForm(),
        'register_form': register_form,
    }, context_instance=RequestContext(request))

@login_required
def user(request, user_id=None):
    if user_id is not None:
        user = get_object_or_404(User, pk=user_id)
    else:
        user = request.user
    if user != request.user and not request.user.has_perm('auth.change_user'):
        return redirect_to_login(request.path)
    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'promote':
            if not request.user.has_perm('auth.change_user'):
                return redirect_to_login(request.path)
            user.get_profile().promote()
        elif action == 'demote':
            if not request.user.has_perm('auth.change_user'):
                return redirect_to_login(request.path)
            user.get_profile().demote()
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
    profile = get_object_or_404(UserProfile, pk=id)
    user = profile.user
    if user.id != request.user.id and not request.user.has_perm(
        'auth.change_user'):
        return redirect_to_login(request.path)
    userApproved = False
    if profile.generate_confirmation_code() == code:
        userApproved = profile.approved = True
        profile.blocked = False
        profile.save()
        if request.user.id == user.id:
            request.user = user # so it doesn't do the warning bar
        form = None
    else:
        if request.method == 'POST':
            form = user_forms.ConfirmationEmailRequestForm(request.POST)
            if form.is_valid():
                if form.cleaned_data['email']:
                    user.email = form.cleaned_data['email']
                    user.save()
                form = None
        else:
            form = user_forms.ConfirmationEmailRequestForm()
            form.fields['email'].initial = user.email
        if code == "resend":
            profile.send_confirmation_email()
    return render_to_response('user_profile/confirm.html', {
            'approved': userApproved,
            'form' : form,
            'code': code}, context_instance=RequestContext(request))

def edit_user_form(request, user):
    if user.has_perm('channels.change_channel'):
        FormClass = user_forms.EditModeratorForm
    elif user.channels.count():
        FormClass = user_forms.EditChannelOwnerForm
    else:
        FormClass = user_forms.EditUserForm

    if request.method == 'POST':
        form = FormClass(user, request.POST)
        if form.is_valid():
            form.update_user(request)
            return util.redirect(request.path)
    else:
        form = FormClass(user)
    return render_to_response('user_profile/edit-user.html', {
            'for_user':user,
            'form': form}, context_instance=RequestContext(request))

@permission_required('user_profile.list_users')
def search(request):
    query = request.GET.get('query', '')
    if not query:
        page = None
    else:
        user_query = User.objects.filter(Q(username__icontains=query) |
                Q(email__icontains=query))
        paginator = Paginator(user_query, 10)
        page = paginator.page(request.GET.get('page', 1))

    return render_to_response('user_profile/user-search.html', {
            'query': query,
            'page': page,
            }, context_instance=RequestContext(request))

@permission_required('user_profile.list_users')
def moderators(request):
    moderator_group = Group.objects.get(name='cg_moderator')
    paginator = Paginator(moderator_group.user_set.all(), 15)
    page = paginator.page(request.GET.get('page', 1))
    return render_to_response('user_profile/moderators.html', {
            'page': page,
            }, context_instance=RequestContext(request))

def set_language_view(request):
    value = request.REQUEST.get('filter', None)
    if request.user.is_authenticated():
        profile = request.user.get_profile()
        if value == '0':
            profile.filter_languages = False
            profile.shown_languages.clear()
            profile.save()
        elif value == '1' and profile.language:
            languageName = settings.ENGLISH_LANGUAGE_MAP.get(
                profile.language)
            if languageName:
                try:
                    dbLanguage = Language.objects.get(name=languageName)
                except Language.DoesNotExist:
                    pass
                else:
                    profile.filter_languages = True
                    profile.shown_languages.clear()
                    profile.shown_languages.add(dbLanguage)
                    profile.save()
    else:
        if value == '0':
            request.session['filter_languages'] = False
        elif value == '1':
            request.session['filter_languages'] = True
        request.session.cycle_key()
    return util.redirect_to_referrer(request)

def for_user(request, user_name_or_id):
    try:
        user = User.objects.get(username=user_name_or_id)
    except User.DoesNotExist:
        try:
            user = get_object_or_404(User, pk=user_name_or_id)
        except ValueError:
            raise Http404
    if not user.is_active:
        raise Http404
    expected_path = '/user/%s' % user.username
    if request.path != expected_path:
        return util.redirect(expected_path)
    if request.user.is_superuser or request.user.id == user.id:
        try:
            cobrand = Cobranding.objects.get(user=user.username)
        except Cobranding.DoesNotExist:
            cobrand = None
    else:
        cobrand = None

    page = request.GET.get('page', 1)

    feed_paginator = Paginator(user.channels.filter(url__isnull=False), 10)
    try:
        feed_page = feed_paginator.page(page)
    except InvalidPage:
        feed_page = None

    site_paginator = Paginator(user.channels.filter(url__isnull=True), 10)
    try:
        site_page = site_paginator.page(page)
    except InvalidPage:
        site_page = None

    # find the biggest paginator and use that page for calculating the links
    if not feed_paginator:
        biggest = site_page
    elif not site_paginator:
        biggest = feed_page
    elif feed_paginator.count > site_paginator.count:
        biggest = feed_page
    else:
        biggest = site_page

    return render_to_response('user_profile/for-user.html', {
            'for_user': user,
            'title': _("Shows for %s") % user.username,
            'cobrand': cobrand,
            'biggest': biggest,
            'feed_page': feed_page,
            'site_page': site_page,
            }, context_instance=RequestContext(request))
