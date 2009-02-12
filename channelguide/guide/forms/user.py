# Copyright (c) 2008 Participatory Culture Foundation
# See LICENSE for details.

from django import forms
from django.utils.translation import ugettext_lazy as _
from django.conf import settings

from channelguide.guide.models import User, Language
from form import Form
from fields import WideCharField, WideEmailField, WideChoiceField

class NewUserField(forms.CharField):
    def clean(self, value):
        rv = super(NewUserField, self).clean(value)
        if rv == self.initial:
            # allow keeping the same username
            return rv
        if User.query(username=value).count(self.connection) > 0:
            raise forms.ValidationError(_("Username already taken"))
        return rv

class NewEmailField(WideEmailField):
    def clean(self, value):
        value = super(NewEmailField, self).clean(value)
        if value == self.initial:
            # don't check if the user isn't changing the value
            return value
        if User.query(email=value).count(self.connection) > 0:
            raise forms.ValidationError(_("E-mail already taken"))
        return value

class ExistingEmailField(WideEmailField):
    def clean(self, value):
        value = super(ExistingEmailField, self).clean(value)
        if User.query(email=value).count(self.connection) == 0:
            raise forms.ValidationError(_("E-mail not found"))
        return value

class UsernameField(forms.CharField):
    def clean(self, value):
        value = super(forms.CharField, self).clean(value)
        try:
            return User.query(username=value).get(self.connection)
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
            return User.query(email=value).get(self.connection)
        except LookupError:
            raise forms.ValidationError(
                _("That username or e-mail is not valid."))

class ShownLanguagesWidget(forms.MultiWidget):
    def __init__(self):
        super(ShownLanguagesWidget, self).__init__((forms.RadioSelect, forms.SelectMultiple))

    def decompress(self, value):
        if not value:
            return ['False', []]
        return value

class ShownLanguagesField(forms.MultiValueField):
    def __init__(self, *args, **kw):
        kw['widget'] = ShownLanguagesWidget()
        kw['required'] = False
        kw['label'] = ''
        args = ((
                forms.ChoiceField(choices=((False, _("Display shows in all languages")),
                                           (True, _("Only display shows in these languages:"))),
                                  initial=''),
                forms.MultipleChoiceField(
                    help_text=_("Hold CTRL to select multiple languages"))),) + args
        super(ShownLanguagesField, self).__init__(*args, **kw)

    def compress(self, values):
        return values

    def clean(self, value):
        if value[0] == 'False':
            filter_languages = False
        else:
            filter_languages = True
        languages = [Language.get(self.connection, lang_id) for lang_id in value[1]]
        return filter_languages, languages

    def update_choices(self):
        languages = Language.query().order_by('name').execute(self.connection)
        self.fields[1].choices = [(language.id, _(language.name))
                                  for language in languages]
        for field, widget in zip(self.fields, self.widget.widgets):
            widget.choices = field.choices

class LoginForm(Form):
    username = UsernameOrEmailField(max_length=20, required=False)
    password = forms.CharField(max_length=20, widget=forms.PasswordInput,
                               required=False)

    def clean_password(self):
        user = self.cleaned_data.get('username')
        password = self.cleaned_data.get('password')
        if user is not None and password is not None:
            if not user.check_password(password):
                raise forms.ValidationError(_("That password is not valid."))
        return password

    def get_user(self):
        return self.cleaned_data.get('username')

class PasswordComparingForm(Form):
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
        user = User(self.cleaned_data['newusername'],
                self.cleaned_data['newpassword'], self.cleaned_data['email'])
        user.save(self.connection)
        user.send_confirmation_email()
        return user

class EditUserForm(PasswordComparingForm):
    username = NewUserField(max_length=100)
    email = NewEmailField(max_length=100, required=False)
    change_password = WideCharField(max_length=30, widget=forms.PasswordInput,
            label=_('Change Password'), required=False)
    change_password2 = WideCharField(max_length=30, widget=forms.PasswordInput,
            label=_("Confirm Password"), required=False)
    fname = WideCharField(max_length=45, required=False,
            label=_("First Name"))
    lname = WideCharField(max_length=45, required=False,
            label=_("Last Name"))
    age = forms.IntegerField(required=False, label=_("Age"))
    gender = WideChoiceField(choices = [('', 'Not Specified'),
                                        ('F', 'Female'),
                                        ('M', 'Male')],
                             label=_("Gender"),
                             required=False)
    city = WideCharField(max_length=45, required=False,
            label=_("City"))
    state = WideCharField(max_length=20, required=False,
            label=_("State"))
    country = WideCharField(max_length=25, required=False,
            label=_("Country"))
    zip = WideCharField(max_length=15, required=False,
            label=_("Zip Code"))
    im_username = WideCharField(max_length=35, required=False,
            label=_("IM Username"))
    im_type = WideCharField(max_length=25, required=False,
            label=_("IM Type"))
    language = WideChoiceField(choices=settings.LANGUAGES,
                               initial=settings.LANGUAGE_CODE,
                               label=_("Show interface in"))
    shown_languages = ShownLanguagesField()

    password_key = 'change_password'
    password_check_key = 'change_password2'

    def __init__(self, connection, user, data=None):
        super(EditUserForm, self).__init__(connection, data)
        self.user = user
        user.join('shown_languages').execute(connection)
        self.set_defaults()

    def simple_fields(self):
        for name, field in self.fields.items():
            if name not in ('change_password', 'change_password2',
                            'shown_languages'):
                yield name, field

    def set_defaults(self):
        self.fields['shown_languages'].initial = (
            self.user.filter_languages,
            [language.id for language in self.user.shown_languages])
        self.fields['shown_languages'].update_choices()
        for name, field in self.simple_fields():
            field.initial = getattr(self.user, name)

    def update_user(self, request):
        for name, field in self.simple_fields():
            if self.cleaned_data.get(name) is not None:
                value = self.cleaned_data[name]
                setattr(self.user, name, self.cleaned_data[name])
        self.user.filter_languages = self.cleaned_data['shown_languages'][0]
        if self.user.shown_languages:
            self.user.shown_languages.clear(self.connection)
        if self.cleaned_data['shown_languages'][1]:
            self.user.shown_languages.add_records(
                self.connection,
                self.cleaned_data['shown_languages'][1])
        if self.cleaned_data.get('change_password'):
            self.user.set_password(self.cleaned_data['change_password'])
        # update language setting
        if self.user is request.user:
            request.session['django_language'] = self.cleaned_data['language']
        self.user.save(self.connection)

class EditChannelOwnerForm(EditUserForm):
    channel_owner_emails = forms.BooleanField(label=_('Channel Owner Emails'),
            required=False)

class EditModeratorForm(EditChannelOwnerForm):
    moderator_board_email = WideChoiceField(label=_('Moderator Board Emails'),
            choices=(('S', _('Normal')),
                ('N', _('No emails')),
                ('A', _('Send all emails'))))
    status_emails = forms.BooleanField(label=_('Channel Status Emails'),
            required=False)

class ChangePasswordForm(PasswordComparingForm):
    password = WideCharField(max_length=30, widget=forms.PasswordInput,
            label=_('Set a new Password'))
    password2 = WideCharField(max_length=30, widget=forms.PasswordInput,
            label=_("Confirm Password"), required=False)

class AuthTokenRequestForm(Form):
    email = ExistingEmailField()

class ConfirmationEmailRequestForm(Form):
    email = NewEmailField()
