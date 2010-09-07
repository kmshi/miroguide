# Copyright (c) 2008-2009 Participatory Culture Foundation
# See LICENSE for details.

import sha

from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.contrib.auth.models import User, Group, Permission
from django.db import models
from django.core.mail import send_mail

from channelguide import util

class UserProfile(models.Model):
    user = models.ForeignKey(User, db_column='username',
                             to_field='username', unique=True)
    role = models.CharField(max_length=1, default='U')
    blocked = models.BooleanField(default=False)
    approved = models.BooleanField(default=False)
    show_explicit = models.BooleanField(False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    fname = models.CharField(max_length=45)
    lname = models.CharField(max_length=45)
    email = models.EmailField(max_length=100)
    city = models.CharField(max_length=45)
    state = models.CharField(max_length=20)
    country = models.CharField(max_length=25)
    zip = models.CharField(max_length=15)
    im_username = models.CharField(max_length=35)
    im_type = models.CharField(max_length=25)
    hashed_password = models.CharField(max_length=40)
    moderator_board_email = models.CharField(max_length=1, default='S')
    status_emails = models.BooleanField(default=True)
    email_updates = models.BooleanField(default=False)
    channel_owner_emails = models.BooleanField(default=True)
    age = models.IntegerField(blank=True, null=True)
    gender = models.CharField(max_length=1)
    language = models.CharField(max_length=5, default='')
    filter_languages = models.BooleanField(default=False)
    shown_languages = models.ManyToManyField('labels.Language',
                                             db_table='user_shown_languages')

    class Meta:
        db_table = 'user'
        permissions = [
            ('betatester', 'Has access to early new features')
            ]

    PASSWORD_SALT = ''
    # I'd like to use salt, but it makes it impossible to convert the old VB
    # user table

    ALL_EMAIL = 'A'
    SOME_EMAIL = 'S'
    NO_EMAIL = 'N'

    groups_in_order = [
        'cg_moderator',
        'cg_supermoderator',
        ]


    @models.permalink
    def get_url(self):
        return ('channelguide.user_profile.views.for_user',
                (self.user.username,))

    @models.permalink
    def get_profile_url(self):
        return ('channelguide.user_profile.views.user',
                (self.user.pk,))

    def get_absolute_url(self):
        return util.make_absolute_url(self.get_url())

    def role_string(self):
        user = self.user
        if user.is_superuser:
            return 'Admin'
        elif Group.objects.get(name='cg_supermoderator') in user.groups.all():
            return 'Supermoderator'
        elif Group.objects.get(name='cg_moderator') in user.groups.all():
            return 'Moderator'
        elif user.has_perm('user_profile.betatester'):
            return 'Beta Tester'
        else:
            return 'User'

    def promote(self):
        if self.user.is_superuser:
            return
        if not self.user.has_perm('user_profile.betatester'):
            perm, _ = Permission.objects.get_or_create(
                name='Has access to early new features',
                content_type=ContentType.objects.get_for_model(self),
                codename='betatester')

            self.user.user_permissions.add(perm)
            del self.user._perm_cache
            return
        for name in self.groups_in_order:
            group = Group.objects.get(name=name)
            if group in self.user.groups.all():
                continue
            else:
                self.user.groups.add(group)
                del self.user._perm_cache
                del self.user._group_perm_cache
                return
        self.user.is_superuser = True
        self.user.save()

    def demote(self):
        if self.user.is_superuser:
            self.user.is_superuser = False
            self.user.save()
            return
        for name in self.groups_in_order[::-1]:
            group = Group.objects.get(name=name)
            if group in self.user.groups.all():
                self.user.groups.remove(group)
                try:
                    del self.user._perm_cache
                except AttributeError:
                    pass
                try:
                    del self.user._group_perm_cache
                except AttributeError:
                    pass
                return
        if self.user.has_perm('user_profile.betatester'):
            self.user.user_permissions.filter(codename='betatester').delete()
            del self.user._perm_cache

    def check_password(self, password):
        hashed = util.hash_string(password)
        return self.hashed_password == hashed

    @models.permalink
    def channel_url(self):
        return ('channelguide.user_profile.views.for_user',
                (self.user.username,))

    def __unicode__(self):
        return self.user.username

    def __repr__(self):
        return 'User(%r)' % self.user.username

    def __eq__(self, other):
        if isinstance(other, UserProfile):
            return self.user == other.user
        else:
            return NotImplemented

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
        return self.im_username or False

    def get_im(self):
        if not self.has_im():
            return ''
        if self.im_type is not None:
            return "%s (%s)" % (self.im_username, self.im_type)
        else:
            return self.im_username

    def generate_confirmation_code(self):
        s = '%s%s%s' % (self.user.id, self.user.username,
                        self.user.date_joined.timetuple())
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
The Miro Guide""" % (self.user.email, url)
        send_mail('Approve your Miro Guide account', body, settings.EMAIL_FROM,
                  [self.user.email])

def on_created_user(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.get_or_create(user=instance)

def create_groups(sender, app, created_models, **kwargs):
    from channelguide.user_profile import models as user_profile_models
    if sender is not user_profile_models:
        return
    permissions = {
        'cg_moderator':
            ['channels.change_channel', 'flags.change_flag',
             'channels.add_site',
             'flags.delete_flag', 'moderate.add_moderatoraction',
             'notes.add_channelnote', 'notes.add_moderatorpost'],
        'cg_supermoderator':
            ['featured.add_featuredqueue', 'featured.change_featuredqueue',
             'notes.delete_moderatorpost', 'channels.change_owner']
        }

    # set up the default groups
    for group_name in permissions:
        group, created = Group.objects.get_or_create(name=group_name)
        if created:
            for app_and_permission in permissions[group_name]:
                app_label, codename = app_and_permission.split('.')
                permission = Permission.objects.get(
                    content_type__app_label=app_label,
                    codename=codename)
                group.permissions.add(permission)

from django.contrib.auth.models import User
models.signals.post_save.connect(on_created_user, sender=User)
models.signals.post_syncdb.connect(create_groups)
