from django import forms

from channelguide.guide.forms.form import Form
from channelguide.guide.forms.user import UsernameOrEmailField

# Stolen from user forms
class HashedPasswordLoginForm (Form):
    username = UsernameOrEmailField (max_length=20, required=False)
    password_hash = forms.CharField (
        max_length=32, widget=forms.PasswordInput, required=False
    )

    def clean_password_hash (self):
        user = self.cleaned_data.get ('username')
        password_hash = self.cleaned_data.get ('password_hash')

        print password_hash
        if user is not None:
            if not user.check_hashed_password (password_hash) or user.blocked:
                raise forms.ValidationError(_("That password is not valid."))
        return password_hash

    def get_user (self):
        return self.cleaned_data.get ('username')