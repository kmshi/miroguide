from django import newforms as forms
from django.utils.translation import gettext as _

from channelguide.guide.models import User
from form import Form
from fields import WideCharField, WideEmailField, WideChoiceField

class NewUserField(WideCharField):
    def clean(self, value):
        rv = super(NewUserField, self).clean(value)
        if User.query(username=value).count(self.connection) > 0:
            raise forms.ValidationError(_("username already taken"))
        return rv

class NewEmailField(WideEmailField):
    def clean(self, value):
        value = super(NewEmailField, self).clean(value)
        if value == self.initial:
            # don't check if the user isn't changing the value
            return value
        if User.query(email=value).count(self.connection) > 0:
            raise forms.ValidationError(_("email already taken"))
        return value

class ExistingEmailField(WideEmailField):
    def clean(self, value):
        value = super(ExistingEmailField, self).clean(value)
        if User.query(email=value).count(self.connection) == 0:
            raise forms.ValidationError(_("email not found"))
        return value

class UsernameField(WideCharField):
    def clean(self, value):
        value = WideCharField.clean(self, value)
        try:
            return User.query(username=value).get(self.connection)
        except LookupError:
            raise forms.ValidationError(_("That username is not valid."))

class LoginForm(Form):
    username = UsernameField(max_length=40)
    password = WideCharField(max_length=40, widget=forms.PasswordInput)

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
    username = NewUserField(max_length=40, label=_("Username"))
    email = NewEmailField(max_length=100, label=_("Email address"))
    password = WideCharField(max_length=40, widget=forms.PasswordInput,
            label=_("Pick a password"))
    password2 = WideCharField(max_length=40, widget=forms.PasswordInput,
            label=_("Re-type the password"), required=False)

    def make_user(self):
        user = User(self.cleaned_data['username'], self.cleaned_data['password'])
        user.save(self.connection)
        return user

class EditUserForm(PasswordComparingForm):
    email = NewEmailField(max_length=100, required=False)
    change_password = WideCharField(max_length=30, widget=forms.PasswordInput,
            label=_('Change Password'), required=False)
    change_password2 = WideCharField(max_length=30, widget=forms.PasswordInput,
            label=_("Confirm Password"), required=False)
    fname = WideCharField(max_length=45, required=False,
            label=_("First Name"))
    lname = WideCharField(max_length=45, required=False,
            label=_("Last Name"))
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

    password_key = 'change_password'
    password_check_key = 'change_password2'

    def __init__(self, connection, user, data=None):
        super(EditUserForm, self).__init__(connection, data)
        self.user = user
        self.set_defaults()

    def simple_fields(self):
        for name, field in self.fields.items():
            if name not in ('change_password', 'change_password2'):
                yield name, field

    def set_defaults(self):
        for name, field in self.simple_fields():
            field.initial = getattr(self.user, name)

    def update_user(self):
        for name, field in self.simple_fields():
            if self.cleaned_data.get(name) is not None:
                setattr(self.user, name, self.cleaned_data[name])
        if self.cleaned_data.get('change_password'):
            self.user.set_password(self.cleaned_data['change_password'])
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
