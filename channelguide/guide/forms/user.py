from django import newforms as forms

from channelguide.guide.models import User
from form import Form
from fields import WideCharField, WideEmailField

class NewUserField(WideCharField):
    def clean(self, value):
        rv = super(NewUserField, self).clean(value)
        if self.db_session.query(User).get_by(username=value):
            raise forms.ValidationError(_("username already taken"))
        return rv

class NewEmailField(WideEmailField):
    def clean(self, value):
        value = super(NewEmailField, self).clean(value)
        if value == self.initial:
            # don't check if the user isn't changing the value
            return value
        if self.db_session.query(User).get_by(email=value):
            raise forms.ValidationError(_("email already taken"))
        return value

class ExistingEmailField(WideEmailField):
    def clean(self, value):
        value = super(ExistingEmailField, self).clean(value)
        if self.db_session.query(User).get_by(email=value) is None:
            raise forms.ValidationError(_("email not found"))
        return value

class UsernameField(WideCharField):
    def clean(self, value):
        value = WideCharField.clean(self, value)
        user = self.db_session.query(User).get_by(username=value)
        if user is None:
            raise forms.ValidationError(_("That username is not valid."))
        else:
            return user

class LoginForm(Form):
    username = UsernameField(max_length=40)
    password = WideCharField(max_length=40, widget=forms.PasswordInput)

    def clean_password(self):
        user = self.clean_data.get('username')
        password = self.clean_data.get('password')
        if user is not None and password is not None:
            if not user.check_password(password):
                raise forms.ValidationError(_("That password is not valid."))
        return password

    def get_user(self):
        return self.clean_data.get('username')

class PasswordComparingForm(Form):
    def clean(self):
        if (self.data['password'] and
                (self.data['password'] != self.data.get('password2'))):
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
        user = User(self.clean_data['username'], self.clean_data['password'])
        self.db_session.save(user)
        return user

class EditUserForm(PasswordComparingForm):
    email = NewEmailField(max_length=100, required=False)
    password = WideCharField(max_length=30, widget=forms.PasswordInput,
            label=_('Change Password'), required=False)
    password2 = WideCharField(max_length=30, widget=forms.PasswordInput,
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

    def __init__(self, db_session, user, data=None):
        super(EditUserForm, self).__init__(db_session, data)
        self.user = user
        self.set_defaults()

    def simple_fields(self):
        for name, field in self.fields.items():
            if name not in ('password', 'password2'):
                yield name, field

    def set_defaults(self):
        for name, field in self.simple_fields():
            field.initial = getattr(self.user, name)

    def update_user(self):
        for name, field in self.simple_fields():
            if self.clean_data.get(name):
                setattr(self.user, name, self.clean_data[name])
        if self.clean_data.get('password'):
            self.user.set_password(self.clean_data['password'])

class ChangePasswordForm(PasswordComparingForm):
    password = WideCharField(max_length=30, widget=forms.PasswordInput,
            label=_('Set a new Password'))
    password2 = WideCharField(max_length=30, widget=forms.PasswordInput,
            label=_("Confirm Password"), required=False)

class AuthTokenRequestForm(Form):
    email = ExistingEmailField()
