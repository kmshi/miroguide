# Copyright (c) 2008-2009 Participatory Culture Foundation
# See LICENSE for details.

from django import forms
from django.utils.translation import ugettext_lazy as _
from django.conf import settings
from django.contrib.auth import authenticate
from django.contrib.auth.models import User

from channelguide.labels.models import Language

class NewUserField(forms.CharField):
    def clean(self, value):
        rv = super(NewUserField, self).clean(value)
        if rv == self.initial:
            # allow keeping the same username
            return rv
        if User.objects.filter(username=value).count():
            raise forms.ValidationError(_("Username already taken"))
        return rv

class NewEmailField(forms.EmailField):
    def clean(self, value):
        value = super(NewEmailField, self).clean(value)
        if value == self.initial:
            # don't check if the user isn't changing the value
            return value
        if User.objects.filter(email=value).count():
            raise forms.ValidationError(_("E-mail already taken"))
        return value

class ExistingEmailField(forms.EmailField):
    def clean(self, value):
        value = super(ExistingEmailField, self).clean(value)
        if User.objects.filter(email=value).count() == 0:
            raise forms.ValidationError(_("E-mail not found"))
        return value

class UsernameField(forms.CharField):
    def clean(self, value):
        value = super(forms.CharField, self).clean(value)
        try:
            return User.objects.get(username=value)
        except LookupError:
            raise forms.ValidationError(_("That username is not valid."))


class UsernameOrEmailField(UsernameField):
    def clean(self, value):
        value = super(forms.CharField, self).clean(value)
        try:
            return UsernameField.clean(self, value)
        except forms.ValidationError:
            pass
        try:
            return User.objects.get(email=value)
        except LookupError:
            raise forms.ValidationError(
                _("That username or e-mail is not valid."))

class ShownLanguagesWidget(forms.MultiWidget):
    def __init__(self):
        super(ShownLanguagesWidget, self).__init__((forms.RadioSelect,
                                                    forms.SelectMultiple))

    def decompress(self, value):
        if not value:
            return ['False', []]
        else:
            return [value[0] and 'True' or 'False', value[1]]

class ShownLanguagesField(forms.MultiValueField):
    def __init__(self, *args, **kw):
        kw['widget'] = ShownLanguagesWidget()
        kw['required'] = False
        kw['label'] = ''
        args = ((
                forms.ChoiceField(
                    choices=(
                        (False, _("Display shows in all languages")),
                        (True, _("Only display shows in these languages:"))),
                                  initial=''),
                forms.MultipleChoiceField(
                    help_text=_("Hold CTRL to select multiple languages"))),
                ) + args
        super(ShownLanguagesField, self).__init__(*args, **kw)

    def compress(self, values):
        return (str(values[0]), values[1])

    def clean(self, value):
        if value[0] == 'False':
            filter_languages = False
        else:
            filter_languages = True
        return filter_languages, [lang_id for lang_id in value[1]]

    def update_choices(self):
        self.fields[1].choices = [(language.id, _(language.name))
                                  for language in Language.objects.all()]
        for field, widget in zip(self.fields, self.widget.widgets):
            widget.choices = field.choices

class LoginForm(forms.Form):
    username = UsernameOrEmailField(max_length=20, required=False)
    password = forms.CharField(max_length=20, widget=forms.PasswordInput,
                               required=False)

    def clean_password(self):
        user = self.cleaned_data.get('username')
        password = self.cleaned_data.get('password')
        if user is not None and password is not None:
            if not user.check_password(password) or user.blocked:
                raise forms.ValidationError(_("That password is not valid."))
        return password

    def get_user(self):
        return self.cleaned_data.get('username')

class PasswordComparingForm(forms.Form):
    password_key = 'password'
    password_check_key = 'password2'

    def clean(self):
        if (self.data.get(self.password_key) and
                (self.data.get(self.password_key) !=
                    self.data.get(self.password_check_key))):
            raise forms.ValidationError(_("Passwords don't match"))
        return super(PasswordComparingForm, self).clean()

class RegisterForm(PasswordComparingForm):
    newusername = NewUserField(max_length=20, label=_("Username"))
    email = NewEmailField(max_length=50, label=_("Email Address"))
    newpassword = forms.CharField(max_length=20, widget=forms.PasswordInput,
            label=_("Pick a Password"))
    newpassword2 = forms.CharField(max_length=20, widget=forms.PasswordInput,
            label=_("Confirm Password"))
    password_key = 'newpassword'
    password_check_key = 'newpassword2'

    def make_user(self):
        user = User.objects.create_user(
            self.cleaned_data['newusername'],
            self.cleaned_data['email'],
            self.cleaned_data['newpassword'])

        user.get_profile().send_confirmation_email()

        return authenticate(username=self.cleaned_data['newusername'],
                            password=self.cleaned_data['newpassword'])

class EditUserForm(PasswordComparingForm):
    username = NewUserField(max_length=100)
    email = NewEmailField(max_length=100, required=False)
    change_password = forms.CharField(max_length=30,
                                      widget=forms.PasswordInput,
                                      label=_('Change Password'),
                                      required=False)
    change_password2 = forms.CharField(max_length=30,
                                       widget=forms.PasswordInput,
                                       label=_("Confirm Password"),
                                       required=False)
    first_name = forms.CharField(max_length=30, required=False,
            label=_("First Name"))
    last_name = forms.CharField(max_length=30, required=False,
            label=_("Last Name"))
    age = forms.IntegerField(required=False, label=_("Age"))
    gender = forms.ChoiceField(choices = [('', 'Not Specified'),
                                        ('F', 'Female'),
                                        ('M', 'Male')],
                             label=_("Gender"),
                             required=False)
    city = forms.CharField(max_length=45, required=False,
            label=_("City"))
    state = forms.CharField(max_length=20, required=False,
            label=_("State"))
    country = forms.CharField(max_length=25, required=False,
            label=_("Country"))
    zip = forms.CharField(max_length=15, required=False,
            label=_("Zip Code"))
    im_username = forms.CharField(max_length=35, required=False,
            label=_("IM Username"))
    im_type = forms.CharField(max_length=25, required=False,
            label=_("IM Type"))
    language = forms.ChoiceField(choices=settings.LANGUAGES,
                               initial=settings.LANGUAGE_CODE,
                               label=_("Show interface in"))
    shown_languages = ShownLanguagesField()

    password_key = 'change_password'
    password_check_key = 'change_password2'

    user_fields = ['username', 'email', 'first_name', 'last_name']

    def __init__(self, user, data=None):
        super(EditUserForm, self).__init__(data)
        self.user = user
        self.set_defaults()

    def simple_fields(self):
        for name, field in self.fields.items():
            if name not in ('change_password', 'change_password2',
                            'shown_languages'):
                yield name, field

    def set_defaults(self):
        profile = self.user.get_profile()
        self.fields['shown_languages'].initial = (
            profile.filter_languages,
            [language.id for language in profile.shown_languages.all()])
        self.fields['shown_languages'].update_choices()
        for name, field in self.simple_fields():
            if name in self.user_fields:
                field.initial = getattr(self.user, name)
            else:
                field.initial = getattr(profile, name)

    def update_user(self, request):
        for name, field in self.simple_fields():
            if self.cleaned_data.get(name) is not None:
                setattr(self.user, name, self.cleaned_data[name])
        profile = self.user.get_profile()
        profile.filter_languages = self.cleaned_data['shown_languages'][0]
        profile.shown_languages.clear()
        if self.cleaned_data['shown_languages'][1]:
            profile.shown_languages.add(
                *self.cleaned_data['shown_languages'][1])
        if self.cleaned_data.get('change_password'):
            self.user.set_password(self.cleaned_data['change_password'])
        # update language setting
        if self.user is request.user:
            request.session['django_language'] = self.cleaned_data['language']
        self.user.save()
        profile.save()

class EditChannelOwnerForm(EditUserForm):
    channel_owner_emails = forms.BooleanField(label=_('Channel Owner Emails'),
            required=False)

class EditModeratorForm(EditChannelOwnerForm):
    moderator_board_email = forms.ChoiceField(
        label=_('Moderator Board Emails'),
        choices=(('S', _('Normal')),
                 ('N', _('No emails')),
                 ('A', _('Send all emails'))))
    status_emails = forms.BooleanField(label=_('Channel Status Emails'),
            required=False)

class ChangePasswordForm(PasswordComparingForm):
    password = forms.CharField(max_length=30, widget=forms.PasswordInput,
            label=_('Set a new Password'))
    password2 = forms.CharField(max_length=30, widget=forms.PasswordInput,
            label=_("Confirm Password"), required=False)

class AuthTokenRequestForm(forms.Form):
    email = ExistingEmailField()

class ConfirmationEmailRequestForm(forms.Form):
    email = NewEmailField()
