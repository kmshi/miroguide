import urllib2

from django import newforms as forms
from django.utils.translation import gettext as _

from channelguide.guide.models import User, Channel
from channelguide.lib import feedparser
from channelguide.guide.feedutil import to_utf8
from fields import WideCharField
from form import Form
from submitform import SubmitChannelForm, EditChannelForm

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

    def clean(self):
        user = self.clean_data.get('username')
        password = self.clean_data.get('password')
        errors = []
        if user is not None and password is not None:
            if not user.check_password(password):
                errors.append(_("That password is not valid."))
        if errors:
            raise forms.ValidationError(errors)
        self.clean_data['user'] = user
        return Form.clean(self)

class RegisterForm(Form):
    username = WideCharField(max_length=40, label=_("Pick a username"))
    email = WideCharField(max_length=100, label=_("Email address"))
    password = WideCharField(max_length=40, widget=forms.PasswordInput,
            label=_("Pick a password"))
    password_check = WideCharField(max_length=40, widget=forms.PasswordInput,
            label=_("Re-type the password"))

    def clean(self):
        username = self.clean_data.get('username')
        email = self.clean_data.get('email')
        password = self.clean_data.get('password')
        password_check = self.clean_data.get('password_check')
        errors = []
        query = self.db_session.query(User)
        if query.get_by(username=username):
            errors.append(_("That username is taken."))
        if query.get_by(email=email):
            errors.append(_("That email address is taken."))
        if password is not None and password != password_check:
            errors.append(_("Passwords don't match"))
        if errors:
            raise forms.ValidationError(errors)
        user = User(username, password)
        self.db_session.save(user)
        self.clean_data['user'] = user
        return Form.clean(self)

class RSSFeedField(WideCharField):
    def clean(self, value):
        url = super(RSSFeedField, self).clean(value)
        url = url.strip()
        if self.db_session.query(Channel).get_by(url=url) is not None:
            msg = _("%s is already a channel in the guide") % url
            raise forms.ValidationError(msg)

        missing_feed_msg = _("We can't find a video feed at that address, "
                "please try again.")
        try:
            stream = urllib2.urlopen(url)
            data = stream.read()
        except:
            raise forms.ValidationError(missing_feed_msg)
        parsed = feedparser.parse(data)
        parsed.url = url
        if not parsed.feed or not parsed.entries:
            raise forms.ValidationError(missing_feed_msg)
        return parsed

class FeedURLForm(Form):
    url = RSSFeedField(label=_("Video Feed URL"))

    def get_feed_data(self):
        data = {}
        parsed = self.clean_data['url']
        data['url'] = parsed.url
        def try_to_get(feed_key):
            try:
                return to_utf8(parsed['feed'][feed_key])
            except KeyError:
                return None
        data['name'] = try_to_get('title')
        data['website_url'] = try_to_get('link')
        data['publisher'] = try_to_get('publisher')
        data['short_description'] = try_to_get('description')
        try:
            data['thumbnail_url'] = to_utf8(parsed['feed'].image.href)
        except AttributeError:
            data['thumbnail_url'] = None
        return data
