from datetime import datetime
import sha

from django.conf import settings
from django.utils.translation import gettext as _

from channelguide import util
from sqlhelper.orm import Record
from channelguide.guide import tables, emailmessages
from channelguide.guide.exceptions import AuthError

class UserBase(object):
    def check_is_authenticated(self):
        if not self.is_authenticated():
            raise AuthError("Moderator Access Required")

    def check_is_moderator(self):
        if not self.is_moderator():
            raise AuthError("Moderator Access Required")

    def check_is_supermoderator(self):
        if not self.is_supermoderator():
            raise AuthError("Super-Moderator Access Required")

    def check_is_admin(self):
        if not self.is_admin():
            raise AuthError("Admin Access Required")

    def check_can_edit(self, channel):
        if not self.can_edit_channel(channel):
            raise AuthError("Permission denied")

    def check_same_user(self, other):
        if self.id != other.id:
            raise AuthError("Access denied for account")

    def is_authenticated(self):
        raise NotImplementedError()
    def is_moderator(self):
        raise NotImplementedError()
    def is_supermoderator(self):
        raise NotImplementedError()
    def is_admin(self):
        raise NotImplementedError()

    def can_edit_channel(self, channel):
        return self.is_moderator() or (self.id == channel.owner_id)

class AnonymousUser(UserBase):
    def __init__(self):
        self.id = -1
    def is_authenticated(self): return False
    def is_moderator(self): return False
    def is_supermoderator(self): return False
    def is_admin(self): return False

class User(UserBase, Record):
    table = tables.user

    USER = 'U'
    MODERATOR = 'M'
    SUPERMODERATOR = 'S'
    ADMIN = 'A'
    PASSWORD_SALT = ''
    # I'd like to use salt, but it makes it impossible to convert the old VB
    # user table

    ALL_EMAIL = 'A'
    SOME_EMAIL = 'S'
    NO_EMAIL = 'N'

    roles_in_order = [USER, MODERATOR, SUPERMODERATOR, ADMIN]

    ALL_MODERATOR_ROLES = (ADMIN, MODERATOR, SUPERMODERATOR)
    ALL_SUPERMODERATOR_ROLES = (ADMIN, SUPERMODERATOR)

    def __init__(self, username, password, email):
        self.username = username
        self.email = email
        self.set_password(password)

    def get_url(self):
        return util.make_url("accounts/%d" % self.id)

    def get_absolute_url(self):
        return util.make_absolute_url("accounts/%d" % self.id)

    def promote(self):
        if self.role == self.ADMIN:
            return
        i = self.roles_in_order.index(self.role)
        self.role = self.roles_in_order[i+1]

    def demote(self):
        if self.role == self.USER:
            return
        i = self.roles_in_order.index(self.role)
        self.role = self.roles_in_order[i-1]

    def is_authenticated(self):
        return True

    def is_admin(self):
        return self.role == self.ADMIN

    def is_supermoderator(self):
        return self.role in self.ALL_SUPERMODERATOR_ROLES

    def is_moderator(self):
        return self.role in self.ALL_MODERATOR_ROLES

    def channel_url(self):
        return "channels/user/%d" % self.id

    def __unicode__(self):
        return self.username

    def __repr__(self):
        return 'User(%r)' % self.username

    def __eq__(self, other):
        if isinstance(other, User):
            return self.username == other.username
        else:
            return NotImplemented
    def role_string(self):
        if self.role == self.USER:
            return "user"
        elif self.role == self.MODERATOR:
            return "moderator"
        elif self.role == self.SUPERMODERATOR:
            return "super-mod"
        elif self.role == self.ADMIN:
            return "admin"

    def set_password(self, password):
        self.hashed_password = util.hash_string(password + self.PASSWORD_SALT)

    def check_password(self, password):
        hashed = util.hash_string(password + self.PASSWORD_SALT)
        return self.hashed_password == hashed

    def make_new_auth_token(self, connection):
        if self.auth_token is None:
            self.auth_token = UserAuthToken()
            self.auth_token.user = self
        else:
            self.auth_token.update_token()
        self.auth_token.save(connection)

    def has_full_name(self):
        return self.fname or self.lname

    def get_full_name(self):
        if not self.has_full_name():
            return ''
        names = []
        if self.fname is not None:
            names.append(self.fname)
        if self.lname is not None:
            names.append(self.lname)
        return ' '.join(names)

    def has_location(self):
        return self.city or self.state or self.country or self.zip

    def get_location(self):
        if not self.has_location():
            return ''
        locs = []
        if self.city is not None:
            locs.append(self.city)
        if self.state is not None:
            locs.append(self.state)
        if self.country is not None:
            locs.append(self.country)
        if self.zip is not None:
            locs.append(self.zip)
        return ', '.join(locs)

    def has_im(self):
        return self.im_username or True

    def get_im(self):
        if not self.has_im():
            return ''
        if self.im_type is not None:
            return "%s (%s)" % (self.im_username, self.im_type)
        else:
            return self.im_username

    def generate_confirmation_code(self):
        s = '%s%s%s' % (self.id, self.username, self.created_at.timetuple())
        return sha.new(s.encode('utf8')).hexdigest()[:16]

    def generate_confirmation_url(self):
        return settings.BASE_URL_FULL + 'accounts/confirm/%s/%s' % (self.id,
                self.generate_confirmation_code())

    def send_confirmation_email(self):
        """
        A new user should receive an e-mail with a code that allows them to
        confirm that the account is active.
        """
        url = self.generate_confirmation_url()
        body = """
You have requested a new user account on Miro Guide and you specified
this address (%s) as your e-mail address.

If you did not do this, simply ignore this e-mail.  To confirm your
registration, please follow this link:

%s

Your ratings will show up, but won't count towards the average until
you use this confirmation link.

Thanks,
The Miro Guide""" % (self.email, url)
        util.send_mail('Approve your Miro Guide account', body, [self.email],
                break_lines=False)


class UserAuthToken(Record):
    table = tables.user_auth_token

    def __init__(self):
        self.update_token()

    def update_token(self):
        self.expires = datetime.now() + settings.AUTH_TOKEN_EXPIRATION_TIME
        self.token = util.random_string(30)

    def is_valid(self):
        return self.expires > datetime.now()

    @staticmethod
    def find_token(connection, string):
        try:
            token = UserAuthToken.query(token=string).get(connection)
        except LookupError:
            return None
        if token.is_valid():
            return token
        else:
            token.delete(connection)
            return None

    def send_email(self):
        url = util.make_absolute_url('accounts/change-password', 
                {'token': self.token})
        message = emailmessages.ForgotPasswordEmail(url, self.user)
        message.send_email(self.user.email, break_lines=False)

class FeaturedEmail(Record):
    table = tables.featured_email

class ModeratorAction(Record):
    table = tables.moderator_action

    def __init__(self, user, channel, action):
        self.user = user
        self.channel = channel
        self.action = action

    def get_action_name(self):
        return tables.name_for_state_code(self.action)
    action_name = property(get_action_name)
